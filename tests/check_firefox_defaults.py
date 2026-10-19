"""Check editable Firefox defaults with an isolated RPM Firefox and real profiles.

Run from the repository root with python3 tests/check_firefox_defaults.py. Requires
Firefox, RPM, Bubblewrap, and permission to use local sockets/user namespaces.
Mounts the policy over Firefox's distribution directory only inside Bubblewrap;
never changes the installed browser or an existing user profile. Marionette uses
an ephemeral loopback port. Content sandbox disabling is restricted to this test.
Checks policy loading, pin order/labels, unlocked preferences and saved overrides
across restart. Does not establish image-build or graphical guest behavior.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time

POLICY = Path('build_files/firefox-policies.json').resolve()
EXPECTED = [
    ('ControlThings Website', 'https://www.controlthings.io'),
    ('ControlThings Discord', 'https://discord.gg/controlthings'),
    ('ICS410', 'https://www.sans.org/ics410'),
    ('SANS ICS', 'https://ics.sans.org'),
    ('CS2AI', 'https://www.cs2ai.org/'),
    ('Fedora Project', 'https://fedoraproject.org/start/'),
]


class Browser:
    """Manage one temporary-profile session; fail on protocol or startup errors."""

    def __init__(self, root, firefox_dir):
        self.root = root
        self.firefox_dir = firefox_dir
        self.sequence = 0

    def __enter__(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        profile = self.root / 'profile'
        profile.mkdir(exist_ok=True)
        (profile / 'user.js').write_text(
            f'user_pref("marionette.port", {port});\n'
            'user_pref("browser.shell.checkDefaultBrowser", false);\n'
        )
        (self.root / 'runtime').mkdir(exist_ok=True, mode=0o700)
        self.log = (self.root / 'firefox.log').open('w')
        self.process = subprocess.Popen([
            'bwrap', '--die-with-parent', '--unshare-pid', '--ro-bind', '/', '/', '--bind', str(self.root), str(self.root),
            '--bind', str(self.root / 'distribution'), str(self.firefox_dir / 'distribution'),
            '--dev', '/dev', '--proc', '/proc', str(self.firefox_dir / 'firefox'),
            '--headless', '--no-remote', '--profile', str(profile), '--marionette',
            '--remote-allow-system-access', 'about:blank',
        ], env=dict(os.environ, MOZ_HEADLESS='1', MOZ_DISABLE_CONTENT_SANDBOX='1',
                    MOZ_MARIONETTE='1', XDG_RUNTIME_DIR=str(self.root / 'runtime'),
                    XDG_CACHE_HOME=str(self.root / 'cache')),
            stdout=self.log, stderr=self.log, start_new_session=True)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    self.socket = socket.create_connection(('127.0.0.1', port), timeout=0.5)
                    break
                except OSError:
                    if self.process.poll() is not None:
                        raise RuntimeError((self.root / 'firefox.log').read_text())
                    time.sleep(0.1)
            else:
                raise TimeoutError('Firefox did not open its local Marionette socket')
            self.socket.settimeout(30)
            self.stream = self.socket.makefile('rb')
            assert self.receive()['marionetteProtocol'] == 3
            result = self.command('WebDriver:NewSession', {})
            self.version = result['capabilities']['browserVersion']
            self.command('Marionette:SetContext', {'value': 'chrome'})
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def receive(self):
        """Read a length-prefixed Marionette JSON packet, rejecting truncated data."""
        prefix = b''
        while (char := self.stream.read(1)) != b':':
            if not char:
                raise EOFError('Marionette closed the connection')
            prefix += char
        return json.loads(self.stream.read(int(prefix)))

    def command(self, name, parameters):
        self.sequence += 1
        payload = json.dumps([0, self.sequence, name, parameters]).encode()
        self.socket.sendall(str(len(payload)).encode() + b':' + payload)
        response = self.receive()
        assert response[:2] == [1, self.sequence], response
        if response[2]:
            raise RuntimeError(response[2])
        return response[3]

    def execute(self, script, *args):
        return self.command('WebDriver:ExecuteScript', {'script': script, 'args': args})['value']

    def __exit__(self, *_):
        if hasattr(self, 'stream'):
            try:
                self.command('Marionette:Quit', {'flags': ['eForceQuit']})
            except (OSError, EOFError, RuntimeError):
                pass
            self.stream.close()
            self.socket.close()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait()
        self.log.close()


def snapshot(browser, names):
    """Return effective values and locks, plus the pins Firefox actually consumes."""
    return browser.execute('''
        const names = arguments[0];
        const p = Services.prefs;
        const {NewTabUtils} = ChromeUtils.importESModule("resource://gre/modules/NewTabUtils.sys.mjs");
        return {
            values: Object.fromEntries(names.map(n => [n,
                p.getPrefType(n) == p.PREF_BOOL ? p.getBoolPref(n) :
                p.getPrefType(n) == p.PREF_INT ? p.getIntPref(n) : p.getStringPref(n)])),
            locked: names.filter(n => p.prefIsLocked(n)),
            pins: NewTabUtils.pinnedLinks.links,
            active: Services.policies.status == Services.policies.ACTIVE
        };
    ''', names)


def main():
    policy = json.loads(POLICY.read_text())['policies']
    preferences = policy['Preferences']
    assert all(item['Status'] == 'default' for item in preferences.values())
    pins = json.loads(preferences['browser.newtabpage.pinned']['Value'])
    assert [(pin['label'], pin['url']) for pin in pins] == EXPECTED
    assert preferences['browser.newtabpage.activity-stream.topSitesRows']['Value'] == 1
    firefox_dir = Path(subprocess.check_output(['rpm', '--eval', '%{_libdir}'], text=True).strip()) / 'firefox'
    expected = {name: item['Value'] for name, item in preferences.items()}
    names = list(expected) + ['browser.startup.homepage', 'browser.startup.page']
    with tempfile.TemporaryDirectory(prefix='ct-firefox-defaults-') as temporary:
        root = Path(temporary)
        (root / 'distribution').mkdir()
        shutil.copyfile(POLICY, root / 'distribution/policies.json')
        with Browser(root, firefox_dir) as browser:
            state = snapshot(browser, names)
            assert state['active'] and not state['locked'], state
            assert all(state['values'][key] == value for key, value in expected.items()), state
            assert state['values']['browser.startup.homepage'].rstrip('/') == 'https://www.controlthings.io'
            assert state['values']['browser.startup.page'] == 1
            assert state['pins'] == pins, state['pins']
            browser.execute('''
                Services.prefs.setStringPref("browser.startup.homepage", "https://example.org/personal");
                Services.prefs.setIntPref("browser.startup.page", 3);
                Services.prefs.setBoolPref("browser.newtabpage.activity-stream.widgets.enabled", true);
                const {NewTabUtils} = ChromeUtils.importESModule("resource://gre/modules/NewTabUtils.sys.mjs");
                NewTabUtils.pinnedLinks.pin({url: "https://example.org/personal", label: "Personal shortcut"}, 0);
                Services.prefs.savePrefFile(null);
            ''')
            print(f'PASS Firefox {browser.version}: active policy, defaults, six ordered pins, editable preferences')
        with Browser(root, firefox_dir) as browser:
            state = snapshot(browser, names)
            assert state['values']['browser.startup.homepage'] == 'https://example.org/personal', state
            assert state['values']['browser.startup.page'] == 3
            assert state['values']['browser.newtabpage.activity-stream.widgets.enabled'] is True
            assert state['pins'][0]['label'] == 'Personal shortcut', state['pins']
            assert not state['locked']
            print('PASS personal homepage, session restore, widgets and edited pin survive Firefox restart')


if __name__ == '__main__':
    main()
