"""Check real sysusers, ownership and privilege dropping in a private Bubblewrap root.

Run under unshare --user --map-auto --map-root-user, or sudo python3.
Only temporary fixture files are writable; no host account,
package or service changes occur. uv is a fixture verifying its real UID/GID and
environment before simulating packages. Requires bwrap and systemd-sysusers.
Pass --live to instead download actual tools into the temporary root and exercise
the real helper/install/update/inventory path with network access and managed Python.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LIVE = sys.argv[1:] == ['--live']
if sys.argv[1:] and not LIVE:
    raise SystemExit('Only --live is supported')
if os.geteuid() != 0:
    raise SystemExit('Run under unshare --user --map-auto --map-root-user (private filesystem only)')

with tempfile.TemporaryDirectory(prefix='uv-tools-sandbox-') as temporary:
    work = Path(temporary)
    work.chmod(0o755)
    for directory in ('etc', 'var/lib', 'var/cache', 'run/lock', 'libexec', 'share', 'sysusers', 'units'):
        (work / directory).mkdir(parents=True, exist_ok=True)
    (work / 'etc/passwd').write_text('root:x:0:0:root:/root:/bin/bash\n')
    (work / 'etc/group').write_text('root:x:0:\nwheel:x:10:\n')
    (work / 'etc/shadow').write_text('root:!*:1::::::\n')
    (work / 'etc/gshadow').write_text('root:!::\nwheel:!::\n')
    (work / 'etc/nsswitch.conf').write_text('passwd: files\ngroup: files\nshadow: files\n')
    if LIVE:
        (work / 'etc/resolv.conf').write_bytes(Path('/etc/resolv.conf').read_bytes())
    shutil.copyfile(ROOT / 'system_files/usr/libexec/uv-tools', work / 'libexec/uv-tools')
    (work / 'libexec/uv-tools').chmod(0o755)
    shutil.copyfile(ROOT / 'system_files/usr/lib/sysusers.d/uv-tools.conf', work / 'sysusers/uv-tools.conf')
    for unit in ('uupd.service', 'uupd-manual.service'):
        shutil.copyfile(Path('/usr/lib/systemd/system') / unit, work / 'units' / unit)
        shutil.copytree(ROOT / f'system_files/usr/lib/systemd/system/{unit}.d', work / 'units' / f'{unit}.d')
    for name in ('uv-tools.json', 'uv.toml'):
        shutil.copyfile(ROOT / f'system_files/usr/share/controlthings/{name}', work / 'share' / name)
    (work / 'share/tui-smoke.py').write_text('''
import importlib
import sys
import ctui.application
from prompt_toolkit.application import Application
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

with create_pipe_input() as pipe:
    class SmokeApplication(Application):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, input=pipe, output=DummyOutput(), **kwargs)
        def run(self):
            return super().run(pre_run=lambda: self.exit())
    ctui.application.Application = SmokeApplication
    importlib.import_module(sys.argv[1] + '.commands').main()
''')
    fixture = work / 'uv'
    fixture.write_text('''#!/usr/bin/python3 -I
import json, os, sys
from pathlib import Path
assert os.getuid() == os.getgid() == 395
assert os.getgroups() == []
assert 'UV_INDEX_URL' not in os.environ
assert 'PYTHONPATH' not in os.environ
assert sys.argv[1:3] == ['--config-file', '/usr/share/controlthings/uv.toml']
base = Path('/var/lib/uv-tools')
assert Path.cwd() == base / 'home'
assert os.environ['UV_TOOL_DIR'] == str(base / 'tools')
assert os.environ['UV_PYTHON_INSTALL_DIR'] == str(base / 'python')
args = sys.argv[3:]
cache = Path('/var/cache/uv-tools')
with (cache / 'calls').open('a') as stream:
    stream.write(json.dumps(args) + '\\n')
if (cache / 'fail').exists() and args[:2] == ['tool', 'install']:
    sys.exit(23)
state = base / 'tools/state.json'
packages = json.loads(state.read_text()) if state.exists() else {}
if args[:2] == ['tool', 'install']:
    name = args[-1]
    packages[name] = '1.0'
    state.write_text(json.dumps(packages))
    manifest = json.loads(Path('/usr/share/controlthings/uv-tools.json').read_text())
    for command in next(t for t in manifest['tools'] if t['package'] == name)['commands']:
        script = base / 'bin' / command
        script.write_text('#!/bin/sh\\necho fixture\\n')
        script.chmod(0o755)
elif args[:2] == ['tool', 'list']:
    for name, version in packages.items(): print(f'{name} v{version}')
elif args == ['--version']: print('uv fixture')
elif args[:3] == ['--offline', 'python', 'list']: print('[]')
elif args[:3] == ['--offline', 'pip', 'freeze']: print('fixture==1.0')
elif args[:3] == ['--offline', 'pip', 'check']: pass
elif args == ['python', 'upgrade']: pass
elif args == ['tool', 'upgrade', '--all']: pass
else: raise RuntimeError(args)
''')
    fixture.chmod(0o755)
    if LIVE:
        fixture = Path('/usr/bin/uv')
    command = [
        'bwrap', '--unshare-pid', '--unshare-net', '--unshare-ipc', '--unshare-uts',
        '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
        '--symlink', 'usr/sbin', '/sbin', '--symlink', 'usr/lib', '/lib',
        '--symlink', 'usr/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
        '--perms', '1777', '--tmpfs', '/tmp', '--bind', str(work / 'etc'), '/etc',
        '--bind', str(work / 'var'), '/var', '--bind', str(work / 'run'), '/run',
        '--ro-bind', str(work / 'libexec'), '/usr/libexec',
        '--ro-bind', str(work / 'share'), '/usr/share/controlthings',
        '--ro-bind', str(work / 'sysusers'), '/usr/lib/sysusers.d',
        '--ro-bind', str(work / 'units'), '/units',
        '--ro-bind', str(fixture), '/usr/bin/uv', '--chdir', '/',
        '--setenv', 'UV_INDEX_URL', 'https://untrusted.invalid',
        '--setenv', 'UV_TOOL_DIR', '/attacker', '--setenv', 'PYTHONPATH', '/attacker',
    ]
    if LIVE:
        command.remove('--unshare-net')

    def run(action, success=True):
        """Run the actual helper against fixture accounts and verify its exit status."""
        result = subprocess.run(command + ['/usr/libexec/uv-tools', action], capture_output=True, text=True)
        assert (result.returncode == 0) == success, (action, result.stdout, result.stderr)
        return result

    verified = subprocess.run(command + ['/usr/bin/systemd-analyze', 'verify',
        '/units/uupd.service', '/units/uupd-manual.service'], text=True, capture_output=True)
    assert verified.returncode == 0, verified.stderr

    run('update')  # No payload: no creation or downloads.
    assert not (work / 'var/lib/uv-tools').exists()
    original_passwd = (work / 'etc/passwd').read_text()
    (work / 'etc/passwd').write_text(original_passwd + 'occupied:x:395:395::/:/usr/sbin/nologin\n')
    run('setup', success=False)
    assert 'uv-tools' not in (work / 'etc/group').read_text()
    (work / 'etc/passwd').write_text(original_passwd)
    run('setup')
    assert 'uv-tools:x:395:395:' in (work / 'etc/passwd').read_text()
    assert 'uv-tools:!' in (work / 'etc/shadow').read_text()
    store = work / 'var/lib/uv-tools'
    assert store.stat().st_uid == 0
    assert (store / 'tools').stat().st_uid == 395
    assert (store / 'home').stat().st_mode & 0o777 == 0o700
    if LIVE:
        print('Installing actual packages in private shared paths as UID/GID 395...', flush=True)
        run('install')
        first = json.loads(run('inventory').stdout)
        print(json.dumps(first, indent=2), flush=True)
        run('install')
        assert json.loads(run('inventory').stdout) == first
        run('update')
        after = json.loads(run('inventory').stdout)
        assert set(after['tools']) == {'ctmodbus', 'ctserial', 'greatfet', 'rfcat', 'urh'}
        assert all(name in after['dependencies'] for name in after['tools'])
        target = Path(os.readlink(store / 'bin/urh'))
        assert target.is_relative_to('/var/lib/uv-tools')
        assert (work / str(target).lstrip('/')).is_file()
        offline = command[:1] + ['--unshare-net'] + command[1:]
        result = subprocess.run(offline + ['/usr/bin/setpriv', '--reuid=1000', '--regid=1000',
            '--clear-groups', '--', '/bin/sh', '-c', '''
set -eu
export HOME=/tmp/uv-smoke-home
export XDG_CONFIG_HOME=$HOME/config
export QT_QPA_PLATFORM=offscreen
export PATH=/var/lib/uv-tools/bin:/usr/bin:/usr/sbin
mkdir -p "$HOME"
rfcat --help >/dev/null
greatfet info --help >/dev/null
urh --version
urh autoclose
/var/lib/uv-tools/tools/ctmodbus/bin/python /usr/share/controlthings/tui-smoke.py ctmodbus
/var/lib/uv-tools/tools/ctserial/bin/python /usr/share/controlthings/tui-smoke.py ctserial
'''], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, (result.stdout, result.stderr)
        print('PASS real managed Python install, rerun, update, provenance and offline normal-user startup')
        raise SystemExit(0)
    run('install')
    run('install')
    calls = [json.loads(line) for line in (work / 'var/cache/uv-tools/calls').read_text().splitlines()]
    assert len([call for call in calls if call[:2] == ['tool', 'install']]) == 5
    run('update')
    actual = json.loads(run('inventory').stdout)
    assert set(actual['tools']) == {'ctmodbus', 'ctserial', 'greatfet', 'rfcat', 'urh'}
    assert len(actual['manifest_sha256']) == len(actual['config_sha256']) == 64
    assert len(actual['dependencies']) == 5
    # Installed tools removed from the manifest are still retained/updatable.
    selection = json.loads((work / 'share/uv-tools.json').read_text())
    selection['tools'] = selection['tools'][:-1]
    (work / 'share/uv-tools.json').write_text(json.dumps(selection))
    run('install')
    assert (store / 'bin/urh').exists()
    # A normal user can execute shared commands but cannot replace them or invoke
    # privileged maintenance. Drop identity only inside the fixture.
    result = subprocess.run(command + ['/usr/bin/setpriv', '--reuid=1000', '--regid=1000',
        '--clear-groups', '--', '/bin/sh', '-c',
        '/var/lib/uv-tools/bin/rfcat && ! test -w /var/lib/uv-tools/bin/rfcat && '
        '! /usr/libexec/uv-tools install'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    # Interrupted installs return failure and can be retried without resetting others.
    state = store / 'tools/state.json'
    packages = json.loads(state.read_text())
    del packages['rfcat']
    state.write_text(json.dumps(packages))
    (work / 'var/cache/uv-tools/fail').touch()
    run('install', success=False)
    (work / 'var/cache/uv-tools/fail').unlink()
    run('install')
    # Unsafe shared directory ownership and lock symlinks are rejected.
    (store / 'bin').chmod(0o777)
    run('update', success=False)
    (store / 'bin').chmod(0o755)
    lock = work / 'run/lock/uv-tools.lock'
    lock.unlink()
    lock.symlink_to('/etc/passwd')
    before = (work / 'etc/passwd').read_bytes()
    run('update', success=False)
    assert (work / 'etc/passwd').read_bytes() == before

print('PASS isolated real sysusers, UID/GID drop, protected stores, reruns, metadata and failure recovery')
