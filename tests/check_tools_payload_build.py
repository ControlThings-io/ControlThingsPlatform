"""Check the real payload-builder shell in an isolated Bubblewrap filesystem.

Requires bwrap, Bash, Python, tar and zstd. Brew/Flatpak/user-switch/mount commands
are fixtures; real bootstrap extraction and metadata capture run unchanged. No actual
packages are downloaded or installed. Native package installation needs CI.
"""

from pathlib import Path
import hashlib
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def executable(path: Path, body: str) -> None:
    """Write a fixture shell executable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!/usr/bin/bash\nset -euo pipefail\n' + body)
    path.chmod(0o755)


with tempfile.TemporaryDirectory(prefix='ct-payload-build-') as temporary:
    work = Path(temporary)
    for name in ('var', 'flatpak', 'out', 'tmp/bin', 'libexec', 'manifests'):
        (work / name).mkdir(parents=True)
    custom = ROOT / 'system_files/usr/share/ublue-os/homebrew/controlthings.Brewfile'
    (work / 'manifests/controlthings.Brewfile').write_bytes(custom.read_bytes())
    (work / 'manifests/system-flatpaks.Brewfile').write_text(
        'flatpak "org.mozilla.firefox"\nflatpak "io.github.kolunmi.Bazaar"\nflatpak "dk.gqrx.gqrx"\n')
    (work / 'manifests/cli.Brewfile').write_text('brew "forbidden-optional-tool"\n')
    (work / 'manifests/system-dx-flatpaks.Brewfile').write_text('flatpak "org.optional.App"\n')
    prefix = work / 'original/home/linuxbrew/.linuxbrew'
    executable(prefix / 'bin/brew', '''
printf 'brew %s\\n' "$*" >> /tmp/commands
case "$1" in
    update) ;;
    bundle)
        test "${HOMEBREW_NO_AUTO_UPDATE}" = 1
        test "${HOME}" = /home/linuxbrew
        test -f /tmp/controlthings.Brewfile
        ! /usr/bin/grep -q flatpak /tmp/controlthings.Brewfile
        mkdir -p /home/linuxbrew/.linuxbrew/Cellar/fixture/1.0
        echo fixture > /home/linuxbrew/.linuxbrew/Cellar/fixture/1.0/installed
        ;;
    list) echo 'fixture 1.0' ;;
    cleanup) ;;
    *) exit 1 ;;
esac
''')
    inherited = work / 'homebrew.tar.zst'
    subprocess.run(['tar', '--zstd', '--owner=0', '--group=0', '-cf', str(inherited), '-C', str(work / 'original'),
                    'home/linuxbrew/.linuxbrew'], check=True)
    for name in ('useradd', 'chown', 'mount'):
        executable(work / 'tmp/bin' / name, f'echo "{name} $*" >> /tmp/commands\n')
    executable(work / 'tmp/bin/bwrap', '''
echo "bwrap $*" >> /tmp/commands
test "$*" = '--unshare-net --ro-bind / / /usr/bin/true'
test "${CT_TEST_FAIL_SANDBOX:-0}" = 0
''')
    executable(work / 'tmp/bin/runuser', '''
test "$1" = -u
test "$2" = ct-brew-build
test "$3" = --
echo 'runuser ct-brew-build' >> /tmp/commands
shift 3
exec "$@"
''')
    executable(work / 'tmp/bin/flatpak', '''
echo "flatpak $*" >> /tmp/commands
case "$1" in
    --default-arch) echo x86_64 ;;
    remote-ls)
        if [[ "${CT_TEST_FAIL_CATALOG:-0}" == 1 ]]; then exit 1; fi
        python3 /usr/libexec/controlthings-tools disk-selection | \
            python3 -c 'import json,sys; print("\\n".join(json.load(sys.stdin)["flatpak"]))'
        ;;
    remote-add) mkdir -p /var/lib/flatpak/repo; echo signed-flathub > /var/lib/flatpak/repo/config ;;
    config) ;;
    install)
        [[ " $* " != *" --no-deploy "* ]]
        [[ " $* " == *" org.mozilla.firefox "* ]]
        [[ " $* " == *" io.github.kolunmi.Bazaar "* ]]
        [[ " $* " != *" org.optional.App "* ]]
        mkdir -p /var/lib/flatpak/app/org.controlthings.Fixture
        echo installed-app > /var/lib/flatpak/app/org.controlthings.Fixture/fixture
        ;;
    *) exit 1 ;;
esac
''')
    executable(work / 'tmp/bin/ostree', '''
case "$2" in
    refs) echo flathub:app/org.controlthings.Fixture/x86_64/stable ;;
    rev-parse) echo fixture-commit ;;
    *) exit 1 ;;
esac
''')
    helper = work / 'libexec/controlthings-tools'
    helper.write_bytes((ROOT / 'system_files/usr/libexec/controlthings-tools').read_bytes())
    command = [
        'bwrap', '--unshare-user', '--uid', '0', '--gid', '0',
        '--unshare-pid', '--unshare-ipc', '--unshare-uts',
        '--ro-bind', '/usr', '/usr', '--ro-bind', '/etc', '/etc',
        '--symlink', 'usr/bin', '/bin', '--symlink', 'usr/sbin', '/sbin',
        '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
        '--proc', '/proc', '--dev', '/dev', '--bind', str(work / 'var'), '/var',
        '--symlink', 'var/home', '/home',
        '--bind', str(work / 'flatpak'), '/var/lib/flatpak',
        '--bind', str(work / 'out'), '/out',
        '--bind', str(work / 'tmp'), '/tmp',
        '--ro-bind', str(work / 'libexec'), '/usr/libexec',
        '--ro-bind', str(inherited), '/usr/share/homebrew.tar.zst',
        '--ro-bind', str(work / 'manifests'),
        '/usr/share/ublue-os/homebrew',
        '--ro-bind', str(ROOT / 'disk_config/tools/build-tools.sh'), '/build-tools.sh',
        '--setenv', 'PATH', '/tmp/bin:/usr/bin:/usr/sbin',
        '/usr/bin/bash', '/build-tools.sh',
    ]
    # Match the build container: /home is dangling until the script creates
    # /var/home. Pre-binding /var/home would hide the first disk CI failure.
    assert not (work / 'var/home').exists()
    subprocess.run(command, check=True)
    assert (work / 'var/home/linuxbrew/.linuxbrew/Cellar/fixture/1.0/installed').read_text() == 'fixture\n'
    assert (work / 'flatpak/app/org.controlthings.Fixture/fixture').read_text() == 'installed-app\n'
    assert (work / 'out/homebrew-versions.txt').read_text() == 'fixture 1.0\n'
    assert (work / 'out/flatpak-architecture.txt').read_text() == 'x86_64\n'
    assert 'fixture-commit' in (work / 'out/flatpak-commits.txt').read_text()
    commands = (work / 'tmp/commands').read_text()
    assert commands.count('runuser ct-brew-build') == 4
    assert '--no-deploy' not in commands
    assert 'chown -R 1000:1000 /home/linuxbrew/.linuxbrew' in commands
    assert not list((work / 'out').glob('*.tar.zst'))
    installed = json.loads((work / 'out/installed.json').read_text())
    assert installed['homebrew_versions'] == ['fixture 1.0']
    assert installed['manifests_sha256']['controlthings.Brewfile'] == hashlib.sha256(custom.read_bytes()).hexdigest()
    assert set(installed['manifests_sha256']) == {'controlthings.Brewfile', 'system-flatpaks.Brewfile'}
    assert 'org.mozilla.firefox' in installed['flatpak']
    assert 'io.github.kolunmi.Bazaar' in installed['flatpak']
    assert installed['flatpak'].count('dk.gqrx.gqrx') == 1
    assert 'org.optional.App' not in installed['flatpak']
    assert installed['omitted_aurora_flatpaks'] == []
    assert installed['flatpak_commits'] == {'flathub:app/org.controlthings.Fixture/x86_64/stable': 'fixture-commit'}
    # Catalog failure cannot produce an empty success, and sandbox failure
    # must abort before any download/installation command.
    for failure in ('CT_TEST_FAIL_CATALOG', 'CT_TEST_FAIL_SANDBOX'):
        (work / 'tmp/commands').unlink()
        failure_command = command[:-2] + ['--setenv', failure, '1'] + command[-2:]
        result = subprocess.run(failure_command, text=True, capture_output=True)
        assert result.returncode != 0
        failed_commands = (work / 'tmp/commands').read_text()
        assert 'runuser' not in failed_commands
        if failure == 'CT_TEST_FAIL_SANDBOX':
            assert 'flatpak' not in failed_commands

print('Disk-only payload shell populated Brew/Flatpak stores and metadata in an isolated filesystem')
