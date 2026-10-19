"""Exercise workbook boot seeding and workflow secret cleanup without host changes.

Run from repository root with python3 tests/check_workbook.py. Real tar extraction
uses temporary fixtures; account/systemd/crontab operations are mocked. Does not
prove private Git access, SELinux policy, or systemd boot behavior in a guest.
"""
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import textwrap

with tempfile.TemporaryDirectory(prefix='workbook-test-') as tmp:
    root = Path(tmp)
    seed = root / 'seed'
    seed.mkdir()
    source = root / 'source'
    resources = source / 'workbook/resources'
    resources.mkdir(parents=True)
    (resources / 'ewb-update.cron').write_text('fixture cron\n')
    (resources / 'workbook-update.sh').write_text('#!/bin/bash\nexit 0\n')
    (source / 'workbook/index.html').write_text('initial')
    credentials = source / 'workbook-update/.ssh'
    credentials.mkdir(parents=True)
    (credentials / 'workbook_key').write_text('fixture credential')
    (credentials / 'workbook_key').chmod(0o600)
    with tarfile.open(seed / 'seed.tar', 'w') as archive:
        for name in ('workbook', 'workbook-update'):
            archive.add(source / name, arcname=name)
    (seed / 'resources').write_text('resources\n')
    state = root / 'state'
    script = Path('system_files/usr/libexec/ics410-workbook-init').read_text()
    script = script.replace('/usr/share/ics410-workbook', str(seed))
    script = script.replace('/var/lib/ics410', str(state))
    mock = root / 'bin'
    mock.mkdir()
    log = root / 'calls'
    for name in ('chown', 'crontab', 'systemctl'):
        command = mock / name
        command.write_text('#!/bin/bash\nprintf "%s\\n" "$0 $*" >> "$CALL_LOG"\n'
                           'if [[ ${FAIL_CRON:-0} == 1 && $0 == */crontab ]]; then exit 1; fi\n')
        command.chmod(0o755)
    env = dict(os.environ, PATH=f'{mock}:{os.environ["PATH"]}', CALL_LOG=str(log))
    def initialize(**extra):
        return subprocess.run(['bash', '-c', script], env=dict(env, **extra), capture_output=True)
    assert initialize(FAIL_CRON='1').returncode != 0
    assert not (state / '.workbook-cron-installed').exists()
    assert initialize().returncode == 0
    assert (state / 'workbook/index.html').read_text() == 'initial'
    key = state / 'workbook-update/.ssh/workbook_key'
    assert key.stat().st_mode & 0o777 == 0o600
    (state / 'workbook/index.html').write_text('student state')
    key.write_text('rotated credential')
    updater = state / 'workbook/resources/workbook-update.sh'
    assert updater.stat().st_mode & 0o777 == 0o755
    updater.chmod(0o644)
    before = log.read_text().count('/crontab ')
    assert initialize().returncode == 0
    assert (state / 'workbook/index.html').read_text() == 'student state'
    assert key.read_text() == 'rotated credential'
    assert updater.stat().st_mode & 0o777 == 0o755
    assert log.read_text().count('/crontab ') == before
    assert '--no-block start ewb-update.service' in log.read_text()

    # Execute the actual workflow block with a fake just/sudo, checking cleanup
    # after both successful and failed builds. No real secret is needed.
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
            env=dict(env, L01_PRIVATE_KEY='fixture-secret-text', RUNNER_TEMP=tmp,
                     IMAGE_NAME='fixture', DEFAULT_TAG='ics410_l01', BUILD_EXIT=status))
        assert result.returncode == int(status), result.stderr
        assert not list(root.glob('workbook-key.*'))
        assert 'fixture-secret-text' not in result.stdout + result.stderr
print('PASS seed initialization, retry, persistence, key mode, workflow secret cleanup')

with tempfile.TemporaryDirectory(prefix='workbook-install-') as tmp:
    root = Path(tmp)
    fixture = root / 'remote'
    fixture.mkdir()
    def git(*args):
        subprocess.run(['git', '-C', str(fixture), *args], check=True, capture_output=True)
    git('init', '-b', 'course-default')
    (fixture / 'index.html').write_text('workbook')
    resources = fixture / 'resources'
    resources.mkdir()
    (resources / 'ewb-update.service').write_text('[Service]\nUser=ics410-workbook-update\n')
    (resources / 'ewb-update.cron').write_text('fixture cron\n')
    (resources / 'workbook-update.sh').write_text('#!/bin/bash\n')
    git('add', '.')
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture')
    sandbox = root / 'image'
    for name in ('run/secrets', 'tmp', 'etc', 'usr/bin'):
        (sandbox / name).mkdir(parents=True, exist_ok=True)
    secret = sandbox / 'run/secrets/workbook_key'
    secret.write_text('fixture-private-key-content')
    mock = root / 'bin'
    mock.mkdir()
    programs = {
        'chown': 'exit 0',
        'crontab': 'exit 0',
        'systemctl': 'exit 0',
        'runuser': 'while [[ $1 != -- ]]; do shift; done; shift; exec "$@"',
        'curl': 'while [[ $1 != -o ]]; do shift; done; shift; printf \'{"ssh_keys":["ssh-ed25519 fixture"]}\\n\' > "$1"',
        'install': 'args=(); while (($#)); do case "$1" in -o|-g) shift 2;; *) args+=("$1"); shift;; esac; done; exec /usr/bin/install "${args[@]}"',
        'git': f'if [[ $1 == clone ]]; then shift 2; exec /usr/bin/git clone "{fixture}" "$@"; fi; exec /usr/bin/git "$@"',
    }
    for name, body in programs.items():
        executable = mock / name
        executable.write_text('#!/bin/bash\nset -e\n' + body + '\n')
        executable.chmod(0o755)
    installer = Path('build_files/install-workbook.sh').read_text()
    # Rewrite absolute image paths, leaving command semantics and real Git/tar intact.
    import re
    installer = re.sub(r'/(var|usr|etc|run|tmp)(?=/)',
                       lambda match: str(sandbox) + match.group(0), installer)
    result = subprocess.run(['bash', '-x', '-c', installer], capture_output=True, text=True,
                            env=dict(os.environ, PATH=f'{mock}:{os.environ["PATH"]}'))
    assert result.returncode == 0, result.stderr
    assert secret.read_text() not in result.stdout + result.stderr
    checkout = sandbox / 'var/lib/ics410/workbook'
    assert (checkout / 'index.html').read_text() == 'workbook'
    assert (checkout / '.git').stat().st_mode & 0o777 == 0o700
    assert (checkout / 'resources/workbook-update.sh').stat().st_mode & 0o777 == 0o755
    subprocess.run([str(sandbox / 'usr/bin/workbook-update')], check=True)
    with tarfile.open(sandbox / 'usr/share/ics410-workbook/seed.tar') as archive:
        assert archive.getmember('workbook/resources/workbook-update.sh').mode == 0o755
    assert (sandbox / 'usr/bin/workbook-update').resolve() == checkout / 'resources/workbook-update.sh'
    assert (sandbox / 'usr/share/ics410-workbook/seed.tar').stat().st_mode & 0o777 == 0o600
    branch = subprocess.check_output(['git', '-C', str(checkout), 'branch', '--show-current'], text=True)
    assert branch.strip() == 'course-default'
    assert (checkout / 'resources/ewb-update.service').read_bytes() == (resources / 'ewb-update.service').read_bytes()
print('PASS installer with real default-branch Git clone, seed archive, symlink, permissions, no key tracing')
