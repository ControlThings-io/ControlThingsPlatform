"""Verify the disk image's final COPY instructions with real isolated Podman.

Run with python3; requires working rootless Podman, subordinate UID/GID mappings,
and tar support. Uses scratch fixture stages, private VFS storage and no network.
Checks prefix ownership and Flatpak hardlinks in OCI output without fetching the
Aurora base or executing package installers. Does not test bootc installation.
"""

import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix='ct-disk-oci-') as temporary:
    work = Path(temporary)
    context = work / 'context'
    prefix = context / 'linuxbrew/.linuxbrew/bin'
    prefix.mkdir(parents=True)
    (prefix / 'brew').write_text('brew fixture\n')
    repo = context / 'flatpak/repo/objects'
    repo.mkdir(parents=True)
    (repo / 'fixture').write_text('flatpak fixture\n')
    deployed = context / 'flatpak/app/fixture'
    deployed.parent.mkdir(parents=True)
    os.link(repo / 'fixture', deployed)
    (context / 'installed.json').write_text('{}\n')
    actual = (ROOT / 'disk_config/tools/Containerfile').read_text()
    final = actual.rsplit('FROM ${BASE_IMAGE}', 1)[1]
    (context / 'Containerfile').write_text(
        'FROM scratch AS tools-builder\n'
        'COPY linuxbrew /var/home/linuxbrew\n'
        'COPY flatpak /var/lib/flatpak\n'
        'COPY installed.json /out/installed.json\n'
        'FROM scratch\n' + final)
    runtime = work / 'runtime'
    runtime.mkdir(mode=0o700)
    env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime))
    command = ['podman', '--root', str(work / 'storage'), '--runroot', str(work / 'run'),
               '--storage-driver=vfs', '--events-backend=file', '--tmpdir', str(work / 'tmp')]
    try:
        subprocess.run([*command, 'build', '--pull=never', '--network=none',
                        '--tag', 'localhost/controlthings-disk-fixture:check', str(context)],
                       env=env, check=True)
        output = work / 'oci'
        subprocess.run([*command, 'save', '--format', 'oci-dir', '--output', str(output),
                        'localhost/controlthings-disk-fixture:check'], env=env, check=True)

        def blob(digest: str) -> Path:
            """Locate a content-addressed blob in the emitted OCI directory."""
            algorithm, value = digest.split(':')
            return output / 'blobs' / algorithm / value

        index = json.loads((output / 'index.json').read_text())
        manifest = json.loads(blob(index['manifests'][0]['digest']).read_text())
        members = {}
        for layer in manifest['layers']:
            with tarfile.open(blob(layer['digest']), mode='r:*') as archive:
                for member in archive.getmembers():
                    members[member.name.removeprefix('./').rstrip('/')] = member
        for path in ('var/home/linuxbrew', 'var/home/linuxbrew/.linuxbrew',
                     'var/home/linuxbrew/.linuxbrew/bin/brew'):
            assert members[path].uid == members[path].gid == 1000, (path, members[path])
        files = ['var/lib/flatpak/repo/objects/fixture', 'var/lib/flatpak/app/fixture']
        assert any(members[path].islnk() for path in files), 'Flatpak hardlinks were duplicated'
        assert 'var/lib/controlthings/tools/installed.json' in members
        assert not any(path.endswith('homebrew.tar.zst') or path.endswith('flatpaks.tar.zst')
                       for path in members)
    finally:
        # Podman removes files owned by subordinate UIDs in its own namespace.
        # Every storage/runtime path above belongs to this temporary fixture.
        subprocess.run([*command, 'system', 'reset', '--force'], env=env, check=True)

print('Disk payload COPY preserved Brew ownership and Flatpak hardlinks in real OCI layers')
