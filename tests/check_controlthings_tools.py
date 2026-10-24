"""Check the shared manifest and explicit installer without touching host tools.

Run with python3. External commands and effective ownership are fixtures;
temporary Brewfiles are real. Full Homebrew/Flatpak installation needs disk CI.
"""

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import hashlib
from io import StringIO
import json
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader('tools', str(ROOT / 'system_files/usr/libexec/controlthings-tools'))
spec = spec_from_loader(loader.name, loader)
tools = module_from_spec(spec)
loader.exec_module(tools)
manifest_path = ROOT / 'system_files/usr/share/ublue-os/homebrew/controlthings.Brewfile'
manifest = tools.read_manifest(manifest_path, arch='x86_64')
assert len(manifest['brew']) == 29
assert manifest['flatpak'] == [
    'com.github.tchx84.Flatseal',
    'dk.gqrx.gqrx',
    'io.missioncenter.MissionCenter',
    'io.github.DenysMb.Kontainer',
    'io.github.flattool.Warehouse',
    'io.github.kolunmi.Bazaar',
    'md.obsidian.Obsidian',
    'net.werwolv.ImHex',
    'org.fkoehler.KTailctl',
    'org.gnome.Firmware',
    'org.kde.gwenview',
    'org.kde.kcalc',
    'org.kde.kclock',
    'org.kde.okteta',
    'org.kde.okular',
    'org.zaproxy.ZAP',
]
assert 'ettercap' not in manifest['brew']
arm_manifest = tools.read_manifest(manifest_path, arch='aarch64')
assert arm_manifest['brew'] == manifest['brew']
assert arm_manifest['flatpak'] == [app for app in manifest['flatpak'] if app != 'org.zaproxy.ZAP']
full_manifest_text = manifest_path.read_text()

with tempfile.TemporaryDirectory(prefix='ct-tools-tests-') as temporary:
    for invalid in ('brew "bat"\nbrew "bat"\nflatpak "org.test.App"\n',
                    'brew "bat", args: ["--HEAD"]\n', 'system "bad"\n',
                    'brew "../../bad"\n', 'brew "bat"\n',
                    'brew "bat" # arch=x86_64\nflatpak "org.test.App"\n'):
        bad = Path(temporary) / 'Brewfile'
        bad.write_text(invalid)
        try:
            tools.read_manifest(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Accepted invalid manifest: {invalid}')

    full_manifest = Path(temporary) / 'controlthings.Brewfile'
    full_manifest.write_text(full_manifest_text)
    assert len(tools.read_manifest(full_manifest)['brew']) == 29
    assert len(tools.read_manifest(full_manifest, arch='x86_64')['flatpak']) == 16
    assert len(tools.read_manifest(full_manifest, arch='aarch64')['flatpak']) == 15
    # Upstream defaults come only from the selected container's default list.
    # Duplicate IDs across lists are intentional and must install only once.
    upstream = Path(temporary) / 'system-flatpaks.Brewfile'
    upstream.write_text('flatpak "org.mozilla.firefox"\nflatpak "io.github.kolunmi.Bazaar"\n'
                        'flatpak "dk.gqrx.gqrx"\nflatpak "org.mozilla.thunderbird"\n')
    (Path(temporary) / 'cli.Brewfile').write_text('brew "forbidden-optional-tool"\n')
    (Path(temporary) / 'system-dx-flatpaks.Brewfile').write_text('flatpak "org.optional.App"\n')
    with patch.object(tools, 'AURORA_MANIFEST', upstream), patch.object(tools, 'MANIFEST', full_manifest):
        selected = tools.disk_selection(arch='x86_64')
        assert selected['brew'] == tools.read_manifest(full_manifest)['brew']
        assert selected['flatpak'].count('dk.gqrx.gqrx') == 1
        assert selected['flatpak'][:4] == ['org.mozilla.firefox', 'io.github.kolunmi.Bazaar',
                                         'dk.gqrx.gqrx', 'org.mozilla.thunderbird']
        assert len(selected['flatpak']) == 18
        assert 'org.optional.App' not in selected['flatpak']
        assert set(selected['manifests_sha256']) == {'system-flatpaks.Brewfile', 'controlthings.Brewfile'}
        assert selected['manifests_sha256']['system-flatpaks.Brewfile'] == hashlib.sha256(upstream.read_bytes()).hexdigest()
        with patch.object(tools, 'MANIFEST', manifest_path):
            custom = tools.disk_selection(arch='x86_64', include_aurora=False)
            assert custom['flatpak'] == manifest['flatpak']
            assert custom['brew'] == manifest['brew']
            assert custom['aurora_flatpaks'] == []
            assert custom['profile'] == 'controlthings'
            assert tools.available_disk_selection(custom, set(manifest['flatpak'])) == custom
        assert selected['profile'] == 'full'
        available = set(selected['flatpak'])
        assert tools.available_disk_selection(selected, available)['omitted_aurora_flatpaks'] == []
        for missing in ('org.mozilla.thunderbird', 'dk.gqrx.gqrx'):
            try:
                tools.available_disk_selection(selected, available - {missing})
            except ValueError:
                pass
            else:
                raise AssertionError('Missing AMD64 app was silently omitted')
        arm_selected = tools.disk_selection(arch='aarch64')
        arm_available = set(arm_selected['flatpak']) - {'org.mozilla.thunderbird'}
        filtered = tools.available_disk_selection(arm_selected, arm_available)
        assert filtered['omitted_aurora_flatpaks'] == ['org.mozilla.thunderbird']
        assert 'org.zaproxy.ZAP' not in filtered['flatpak']
        try:
            tools.available_disk_selection(arm_selected, arm_available - {'dk.gqrx.gqrx'})
        except ValueError:
            pass
        else:
            raise AssertionError('Missing custom ARM64 app was silently omitted')
        # Exercise the actual CLI JSON path and warning, with no host manifests.
        catalog = Path(temporary) / 'available.txt'
        catalog.write_text('\n'.join(sorted(arm_available)) + '\n')
        output, errors = StringIO(), StringIO()
        with patch.object(tools.platform, 'machine', return_value='aarch64'), patch.object(
                sys, 'argv', [tools.HELPER, 'disk-selection', '--available-flatpaks', str(catalog)]), patch.object(
                sys, 'stdout', output), patch.object(sys, 'stderr', errors):
            tools.main()
        assert json.loads(output.getvalue()) == filtered
        assert 'org.mozilla.thunderbird' in errors.getvalue()
        upstream.unlink()
        try:
            tools.disk_selection(arch='x86_64')
        except FileNotFoundError:
            pass
        else:
            raise AssertionError('Missing Aurora defaults were ignored')
        upstream.write_text('brew "forbidden-tool"\nflatpak "org.mozilla.firefox"\n')
        try:
            tools.disk_selection(arch='x86_64')
        except ValueError:
            pass
        else:
            raise AssertionError('Unexpected upstream Brew bundle was accepted')

calls = []


def record(*args):
    """Inspect the real temporary Brewfile while recording command delegation."""
    calls.append(args)
    if args[0] == '/fixture/brew':
        path = Path(args[-1].removeprefix('--file='))
        assert path.read_text() == ''.join(f'brew "{name}"\n' for name in manifest['brew'])
        assert '--no-upgrade' in args


brew = MagicMock()
brew.is_file.return_value = True
brew.resolve.return_value.stat.return_value.st_uid = 1000
brew.__str__.return_value = '/fixture/brew'
with patch.object(tools, 'BREW', brew), patch.object(tools, 'run', record):
    for uid in (0, 1001):
        with patch.object(tools.os, 'geteuid', return_value=uid):
            try:
                tools.install(manifest['brew'], manifest['flatpak'])
            except RuntimeError:
                pass
            else:
                raise AssertionError('Root or a different Brew owner was accepted')
        assert not calls
    with patch.object(tools.os, 'geteuid', return_value=1000):
        tools.install(manifest['brew'], manifest['flatpak'])
    assert calls[1][0:3] == ('flatpak', 'remote-add', '--system')
    assert calls[2][0:3] == ('flatpak', 'install', '--system')
    assert calls[-2] == ('flatpak', 'override', '--user', '--socket=x11', 'org.zaproxy.ZAP')
    assert calls[-1] == ('/usr/bin/sudo', '-n', '/usr/libexec/uv-tools', 'install')
    assert all(call[0] not in ('pkexec', 'sudo', '/usr/bin/sudo') for call in calls[:-1])
    calls.clear()
    brew.is_file.return_value = False
    with patch.object(tools.os, 'geteuid', return_value=1000):
        try:
            tools.install(manifest['brew'], manifest['flatpak'])
        except RuntimeError:
            pass
        else:
            raise AssertionError('Missing Brew initialization was ignored')
    assert not calls
    brew.is_file.return_value = True
    with patch.object(tools.os, 'geteuid', return_value=1000), patch.object(
            tools, 'run', side_effect=subprocess.CalledProcessError(1, 'brew')) as command:
        try:
            tools.install(manifest['brew'], manifest['flatpak'])
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError('Brew failure was hidden')
        assert command.call_count == 1  # Failed Brew cannot proceed to Flatpak.

with patch.object(tools, 'run', record):
    tools.install_flatpaks(manifest['flatpak'])
assert calls == [
    ('flatpak', 'remote-add', '--system', '--if-not-exists', 'flathub',
     'https://flathub.org/repo/flathub.flatpakrepo'),
    ('flatpak', 'install', '--system', '--noninteractive', '--assumeyes',
     'flathub', *manifest['flatpak']),
    ('flatpak', 'override', '--user', '--socket=x11', 'org.zaproxy.ZAP'),
]

with patch.object(tools, 'run') as command:
    tools.install_flatpaks(arm_manifest['flatpak'])
    assert all(call.args[1] != 'override' for call in command.call_args_list)

with patch.object(tools, 'read_manifest', return_value=manifest), patch.object(
        tools.os, 'geteuid', return_value=1000), patch.object(
        sys, 'argv', [tools.HELPER, 'install-flatpaks']), patch.object(tools, 'run') as command:
    tools.main()
    assert command.call_args_list[1].args[:3] == ('flatpak', 'install', '--system')
    assert all(call.args[0] == 'flatpak' for call in command.call_args_list)

# Published container builds must never prepare application payloads.
container = (ROOT / 'Containerfile').read_text()
assert 'tools-builder' not in container and 'build-tools.sh' not in container
assert 'TOOLS_BUILD_EPOCH' not in (ROOT / 'Justfile').read_text()
assert not list((ROOT / 'system_files/usr/lib/systemd/system').glob('controlthings-flatpak*'))
assert not hasattr(tools, 'seed_flatpaks')
recipe = ROOT / 'system_files/usr/share/ublue-os/just/60-custom.just'
shown = subprocess.check_output(['just', '--dry-run', '-f', str(recipe),
                                 'install-controlthings-tools'], stderr=subprocess.STDOUT, text=True)
assert '/usr/libexec/controlthings-tools install' in shown
subprocess.run(['bash', '-n', str(ROOT / 'disk_config/tools/build-tools.sh'),
                str(ROOT / 'build_files/build.sh')], check=True)
print('Manifest, explicit installation, failure boundaries and lean container checks passed')
