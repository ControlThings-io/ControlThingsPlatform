"""Check build-time workbook installation and user-launcher forwarding.

Run from repository root with python3 tests/check_workbook.py. Fixtures use real
local Git clones and visudo syntax validation. Account, service, cron, sudo and
network execution are mocked; no host configuration is changed. These checks do
not establish real sudo authorization, SSH access, SELinux or guest boot behavior.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap

with tempfile.TemporaryDirectory(prefix='workbook-workflow-') as tmp:
    root = Path(tmp)
    mock = root / 'bin'
    mock.mkdir()
    env = dict(os.environ, PATH=f'{mock}:{os.environ["PATH"]}')
    workflow = Path('.github/workflows/build.yml').read_text()
    block = workflow.split('        id: build-image\n', 1)[1]
    block = block.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0]
    block = textwrap.dedent(block)
    for name in ('sudo', 'just'):
        command = mock / name
        command.write_text('#!/bin/bash\nexit "${BUILD_EXIT:-0}"\n')
        command.chmod(0o755)
    for status in ('0', '1'):
        result = subprocess.run(['bash', '-c', block], capture_output=True, text=True,
            env=dict(env, L01_PRIVATE_KEY='fixture-secret-text', GITHUB_TOKEN='fixture-api-token', RUNNER_TEMP=tmp,
                     IMAGE_NAME='fixture', DEFAULT_TAG='ics410_l01', BUILD_EXIT=status))
        assert result.returncode == int(status), result.stderr
        assert not list(root.glob('workbook-key.*'))
        assert not list(root.glob('github-token.*'))
        assert 'fixture-api-token' not in result.stdout + result.stderr
        assert 'fixture-secret-text' not in result.stdout + result.stderr
print('PASS workflow secret cleanup on success and failure')

for layout in ('resources', 'docs/resources'):
    with tempfile.TemporaryDirectory(prefix='workbook-install-') as tmp:
        root = Path(tmp)
        fixture = root / 'remote'
        fixture.mkdir()

        def git(*args):
            subprocess.run(['git', '-C', str(fixture), *args], check=True, capture_output=True)

        git('init', '-b', 'course-default')
        (fixture / 'index.html').write_text('workbook')
        resources = fixture / layout
        resources.mkdir(parents=True)
        (resources / 'ewb-update.service').write_text('[Service]\nUser=ics410-workbook-update\n')
        (resources / 'ewb-update.cron').write_text('fixture cron\n')
        (resources / 'workbook-update.sh').write_text(
            '#!/bin/bash\nprintf \'%s\\n\' "$@"\nprintf \'updater stderr\\n\' >&2\nexit 23\n')
        git('add', '.')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture')
        sandbox = root / 'image'
        for name in ('run/secrets', 'tmp', 'etc', 'usr/bin'):
            (sandbox / name).mkdir(parents=True, exist_ok=True)
        secret = sandbox / 'run/secrets/workbook_key'
        secret.write_text('fixture-private-key-content')
        api_token = sandbox / 'run/secrets/github_token'
        if layout == 'resources':
            api_token.write_text('fixture-api-token')
        # Run the real API helper with only its network transport mocked.
        api_runner = root / 'api_fixture.py'
        api_runner.write_text(f'''import sys
sys.dont_write_bytecode = True
sys.path.insert(0, {str(Path('build_files').resolve())!r})
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
import github_api
assert sys.argv[1] == 'https://api.github.com/meta'
def open_response(request, timeout):
    expected = 'Bearer fixture-api-token' if Path({str(api_token)!r}).exists() else None
    assert request.get_header('Authorization') == expected
    stream = BytesIO(b'{{"ssh_keys":["ssh-ed25519 fixture"]}}')
    stream.headers = {{}}
    return stream
with patch.object(github_api, 'build_opener', return_value=Mock(open=open_response)):
    github_api.download(sys.argv[1], Path(sys.argv[2]), Path({str(api_token)!r}))
''')
        mock = root / 'bin'
        mock.mkdir()
        programs = {
            'chown': 'exit 0',
            'crontab': 'printf \'%s\\n\' "$@" > "$CRON_LOG"',
            'systemctl': 'printf \'%s\\n\' "$*" >> "$SERVICE_LOG"',
            'runuser': 'while [[ $1 != -- ]]; do shift; done; shift; exec "$@"',
            'install': 'args=(); while (($#)); do case "$1" in -o|-g) shift 2;; *) args+=("$1"); shift;; esac; done; exec /usr/bin/install "${args[@]}"',
            'git': f'if [[ $1 == clone ]]; then shift 2; exec /usr/bin/git clone "{fixture}" "$@"; fi; exec /usr/bin/git "$@"',
        }
        for name, body in programs.items():
            executable = mock / name
            executable.write_text('#!/bin/bash\nset -e\n' + body + '\n')
            executable.chmod(0o755)
        installer = Path('build_files/install-workbook.sh').read_text()
        # Rewrite image paths; command semantics and real Git/visudo stay intact.
        installer = re.sub(r'/(var|usr|etc|run|tmp)(?=/)',
                           lambda match: str(sandbox) + match.group(0), installer)
        installer = installer.replace('/ctx/github_api.py', str(api_runner))
        result = subprocess.run(['bash', '-x', '-c', installer], capture_output=True, text=True,
            env=dict(os.environ, PATH=f'{mock}:{os.environ["PATH"]}',
                     CRON_LOG=str(root / 'cron'), SERVICE_LOG=str(root / 'services')))
        assert result.returncode == 0, result.stderr
        assert secret.read_text() not in result.stdout + result.stderr
        assert 'fixture-api-token' not in result.stdout + result.stderr
        assert not any('github_token' in path.name for path in (sandbox / 'var').rglob('*'))
        checkout = sandbox / 'var/lib/ics410/workbook'
        assert (checkout / 'index.html').read_text() == 'workbook'
        assert (checkout / '.git').stat().st_mode & 0o777 == 0o700
        assert (checkout / layout / 'workbook-update.sh').stat().st_mode & 0o777 == 0o755
        key = sandbox / 'var/lib/ics410/workbook-update/.ssh/workbook_key'
        assert key.stat().st_mode & 0o777 == 0o600
        launcher = sandbox / 'usr/bin/workbook-update'
        assert launcher.is_file() and not launcher.is_symlink()
        assert launcher.stat().st_mode & 0o777 == 0o755
        assert not (sandbox / 'usr/libexec/ics410-workbook-update').exists()
        sudo = mock / 'sudo'
        sudo.write_text('#!/bin/bash\n'
                        '[[ $1 == -n && $2 == -H && $3 == -u && '
                        '$4 == ics410-workbook-update && $5 == -- && $6 == /bin/bash ]] || exit 99\n'
                        'shift 5; exec "$@"\n')
        sudo.chmod(0o755)
        launcher.write_text(launcher.read_text().replace(str(sandbox / 'usr/bin/sudo'), str(sudo)))
        # Reproduce the guest failure: Git restores the tracked non-executable mode.
        subprocess.run(['git', '-C', str(checkout), 'reset', '--hard'],
                       check=True, capture_output=True)
        assert (checkout / layout / 'workbook-update.sh').stat().st_mode & 0o777 == 0o644
        result = subprocess.run([str(launcher), '-verbose', 'argument with spaces', '; echo unsafe'],
                                capture_output=True, text=True)
        assert result.returncode == 23, result.stderr
        assert result.stdout == '-verbose\nargument with spaces\n; echo unsafe\n'
        assert result.stderr == 'updater stderr\n'
        policy = sandbox / 'etc/sudoers.d/ics410-workbook-update'
        assert policy.stat().st_mode & 0o777 == 0o440
        assert policy.read_text() == ''.join(
            f'ALL ALL=(ics410-workbook-update) NOPASSWD: NOSETENV: '
            f'/bin/bash {checkout}/{layout}/workbook-update.sh{options}\n'
            for options in ('', ' -verbose', ' -debuglog',
                            ' -verbose -debuglog', ' -debuglog -verbose'))
        assert not (sandbox / 'usr/share/ics410-workbook').exists()
        assert not (sandbox / 'usr/lib/systemd/system/ewb-update.service.d').exists()
        assert (root / 'cron').read_text().splitlines() == [
            '-u', 'ics410-workbook-update', str(checkout / layout / 'ewb-update.cron')]
        assert (root / 'services').read_text().splitlines() == [
            f'enable {checkout}/{layout}/ewb-update.service', 'enable ewb-webserver.service']
        branch = subprocess.check_output(['git', '-C', str(checkout), 'branch', '--show-current'], text=True)
        assert branch.strip() == 'course-default'
        assert (checkout / layout / 'ewb-update.service').read_bytes() == (resources / 'ewb-update.service').read_bytes()
print('PASS both resource layouts: full Git checkout, unchanged service, initial cron, launcher arguments/output/status, sudoers syntax')

web = Path('system_files/usr/lib/systemd/system/ewb-webserver.service').read_text()
assert '/var/lib/ics410/workbook' in web
assert 'ics410-workbook-init' not in web
assert '/usr/share/ics410-workbook' not in web
assert not Path('system_files/usr/libexec/ics410-workbook-init').exists()
assert not Path('system_files/usr/lib/systemd/system/ics410-workbook-init.service').exists()
assert not Path('system_files/usr/lib/systemd/system/ics410-workbook-web.service').exists()

workbook_step = Path('Containerfile').read_text().split('ARG WORKBOOK_BUILD_EPOCH=manual', 1)[1].split('### LINTING', 1)[0]
assert '--mount=type=secret,id=workbook_key' in workbook_step
assert '--mount=type=secret,id=github_token' in workbook_step
print('PASS workbook metadata uses shared API authentication, optional local token, and both build-secret mounts')
