"""Verify the disk image's final COPY instructions with real isolated Podman.

Run with python3; requires working rootless Podman, subordinate UID/GID mappings,
and tar support. Uses scratch fixture stages, private VFS storage and no network.
Checks scoped intermediate-image cleanup, OCI transport identity/provenance,
prefix ownership and Flatpak hardlinks
in OCI output without fetching Aurora or running package installers. Does not
test bootc installation or establish sufficient space for full disk builds.
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
        'LABEL io.controlthings.disk-build=fixture\n'
        'COPY linuxbrew /var/home/linuxbrew\n'
        'COPY flatpak /var/lib/flatpak\n'
        'COPY installed.json /out/installed.json\n'
        'FROM scratch\n' + final)
    runtime = work / 'runtime'
    runtime.mkdir(mode=0o700)
    env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime))
    command = ['podman', '--root', str(work / 'storage'), '--runroot', str(work / 'run'),
               '--storage-driver=vfs', '--events-backend=file', '--tmpdir', str(work / 'tmp')]
    receiver = [*command]
    receiver[receiver.index('--root') + 1] = str(work / 'receiver-storage')
    receiver[receiver.index('--runroot') + 1] = str(work / 'receiver-run')
    try:
        subprocess.run([*command, 'build', '--pull=never', '--network=none',
                        '--build-arg', 'BASE_IMAGE=fixture-source@sha256:' + 'a' * 64,
                        '--build-arg', 'PAYLOAD_RECIPE=' + 'b' * 64,
                        '--build-arg', 'UPDATE_REF=fixture-source:latest',
                        '--build-arg', 'SOURCE_REPOSITORY=https://github.com/fixture/source',
                        '--tag', 'localhost/controlthings-disk-fixture:check', str(context)],
                       env=env, check=True)
        # An unrelated dangling image must survive the filtered cleanup too.
        unrelated = context / 'Unrelated'
        unrelated.write_text('FROM scratch\nLABEL io.controlthings.disk-build=other\n')
        subprocess.run([*command, 'build', '--pull=never', '--network=none', '--file', str(unrelated),
                        '--tag', 'localhost/controlthings-unrelated:check', str(context)], env=env, check=True)
        unrelated_id = subprocess.check_output([*command, 'image', 'inspect', '--format', '{{.Id}}',
                                               'localhost/controlthings-unrelated:check'], env=env, text=True).strip()
        subprocess.run([*command, 'untag', 'localhost/controlthings-unrelated:check'], env=env, check=True)
        selected = [*command, 'image', 'ls', '--quiet', '--filter', 'label=io.controlthings.disk-build=fixture']
        assert subprocess.check_output(selected, env=env, text=True).strip()
        subprocess.run([*command, 'image', 'prune', '--force', '--filter',
                        'label=io.controlthings.disk-build=fixture'], env=env, check=True)
        assert not subprocess.check_output(selected, env=env, text=True).strip()
        subprocess.run([*command, 'image', 'inspect', '--format', '{{.Id}}', unrelated_id], env=env, check=True)
        output = work / 'oci'
        subprocess.run([*command, 'save', '--format', 'oci-dir', '--output', str(output),
                        'localhost/controlthings-disk-fixture:check'], env=env, check=True)

        def blob(digest: str) -> Path:
            """Locate a content-addressed blob in the emitted OCI directory."""
            algorithm, value = digest.split(':')
            return output / 'blobs' / algorithm / value

        index = json.loads((output / 'index.json').read_text())
        manifest = json.loads(blob(index['manifests'][0]['digest']).read_text())
        config_id = manifest['config']['digest']
        config = json.loads(blob(config_id).read_text())
        assert config['config']['Labels']['io.controlthings.disk.recipe'] == 'b' * 64
        assert config['config']['Labels']['io.controlthings.disk.channel'] == 'fixture-source:latest'
        # Exercise actual Podman push/digestfile and pull-equivalent load in an
        # empty private store. OCI archive transport needs no registry/network.
        archive_path = work / 'payload.tar'
        digest_path = work / 'payload.digest'
        subprocess.run([*command, 'push', '--digestfile', str(digest_path), config_id,
                        'oci-archive:' + str(archive_path)], env=env, check=True)
        with tarfile.open(archive_path) as archive:
            transported_index = json.load(archive.extractfile('index.json'))
            transported_digest = transported_index['manifests'][0]['digest']
            transported_manifest = json.load(archive.extractfile(
                'blobs/sha256/' + transported_digest.split(':')[1]))
        assert digest_path.read_text().strip() == transported_index['manifests'][0]['digest']
        subprocess.run([*receiver, 'load', '--input', str(archive_path)], env=env, check=True)
        received = json.loads(subprocess.check_output(
            [*receiver, 'image', 'inspect', config_id], env=env, text=True))[0]
        assert received['Id'].removeprefix('sha256:') == config_id.removeprefix('sha256:')
        assert received['Labels'] == config['config']['Labels']
        assert received['RootFS']['Layers'] == config['rootfs']['diff_ids']
        repeated_archive = work / 'republished.tar'
        subprocess.run([*receiver, 'push', config_id, 'oci-archive:' + str(repeated_archive)],
                       env=env, check=True)
        with tarfile.open(repeated_archive) as archive:
            index_again = json.load(archive.extractfile('index.json'))
            manifest_again = json.load(archive.extractfile(
                'blobs/sha256/' + index_again['manifests'][0]['digest'].split(':')[1]))
        assert [layer['digest'] for layer in manifest_again['layers']] == [
            layer['digest'] for layer in transported_manifest['layers']]

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
        assert not any(path.startswith('var/roothome') for path in members)
        assert not any(path.endswith('homebrew.tar.zst') or path.endswith('flatpaks.tar.zst')
                       for path in members)
    finally:
        # Podman removes files owned by subordinate UIDs in its own namespace.
        # Every storage/runtime path above belongs to this temporary fixture.
        for storage in (receiver, command):
            subprocess.run([*storage, 'system', 'reset', '--force'], env=env, check=True)

print('Disk payload COPY/OCI transport preserved identity, provenance, Brew ownership and Flatpak hardlinks')
