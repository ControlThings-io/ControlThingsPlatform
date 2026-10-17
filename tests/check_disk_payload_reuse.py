"""Exercise retained payload identity/reuse without downloads, root or installers.

Run with python3. Registry/Podman are command fixtures. This verifies failure
boundaries and preparation/assembly separation, not registry access permissions
or a real bootc import. The small real OCI transport check lives separately.
"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('disk', 'scripts/build-disk.py')
disk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(disk)
source_digest = 'sha256:' + 'a' * 64
payload_digest = 'sha256:' + 'b' * 64
image_id = 'sha256:' + 'c' * 64
image = 'ghcr.io/controlthings-io/controlthingsplatform'
metadata = {
    'image': image, 'source_ref': f'{image}@{source_digest}',
    'source_digest': source_digest, 'source_tag': 'latest-20261017-5d6b593',
    'update_ref': f'{image}:latest', 'architecture': 'amd64',
    'builder_ref': 'ghcr.io/osbuild/image-builder@sha256:' + 'd' * 64,
}
reference = f'{image}-disk-payload@{payload_digest}'
base_layers = [{'digest': 'sha256:' + 'e' * 64, 'size': 10}]
manifest = {'config': {'digest': image_id},
            'layers': base_layers + [{'digest': 'sha256:' + 'f' * 64, 'size': 20}]}
config = {'architecture': 'amd64', 'os': 'linux',
          'config': {'Labels': disk.payload_labels(metadata)}}
tools = {'architecture': 'x86_64', 'profile': 'smoke',
         'brew': ['ripgrep'], 'flatpak': ['org.kde.okteta']}


def registry(*args, capture=False):
    """Serve only the known immutable fixture manifests/config."""
    assert args[:3] == ('sudo', 'skopeo', 'inspect'), args
    if '--config' in args:
        assert args[-1] == f'docker://{reference}'
        return json.dumps(config)
    if args[-1] == f'docker://{metadata["source_ref"]}':
        return json.dumps({'layers': base_layers})
    assert args[-1] == f'docker://{reference}'
    return json.dumps(manifest)


with patch.object(disk, 'run', side_effect=registry):
    retained = disk.reuse_payload(metadata, reference)
assert retained['payload_image_id'] == image_id
assert retained['payload_layer_bytes'] == '30'
assert retained['payload_ref'] == reference
assert retained['source_ref'] == metadata['source_ref']

for bad in (f'{image}:latest', f'{image}-disk-payload:latest',
            reference.replace('controlthings-io', 'other'), reference + '\n',
            reference.replace(payload_digest, 'sha256:123')):
    with patch.object(disk, 'run') as command:
        try:
            disk.reuse_payload(metadata, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Accepted unsafe/moving payload ref {bad!r}')
        command.assert_not_called()

# Reject stale source, channel, preparation recipe and platform before execution.
for key in ('architecture', 'os', *disk.payload_labels(metadata)):
    bad_config = deepcopy(config)
    if key.startswith(disk.LABEL_PREFIX):
        bad_config['config']['Labels'][key] = 'wrong'
    else:
        bad_config[key] = 'wrong'
    with patch.object(disk, 'run', side_effect=[json.dumps(manifest), json.dumps(bad_config)]):
        try:
            disk.reuse_payload(metadata, reference)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Accepted mismatched {key}')
with patch.object(disk, 'run', return_value='{"manifests": []}'):
    try:
        disk.reuse_payload(metadata, reference)
    except ValueError:
        pass
    else:
        raise AssertionError('Accepted multiarch payload index')

with tempfile.TemporaryDirectory(prefix='ct-payload-reuse-') as temporary:
    root = Path(temporary)
    for kind in ('qcow2', 'iso'):
        output = root / kind
        calls = []

        def assemble(*args, capture=False):
            calls.append(args)
            if args[:3] == ('sudo', 'skopeo', 'inspect'):
                return registry(*args, capture=capture)
            if '{{.Id}}' in args:
                return image_id.removeprefix('sha256:')
            if '--entrypoint' in args:
                return json.dumps(tools)
            if '--output-name' in args:
                name = args[args.index('--output-name') + 1]
                (output / f'{name}.{kind}').write_bytes(b'fixture image')
            return ''

        with patch.object(disk, 'run', side_effect=assemble), patch.object(disk, 'prepare') as prepare:
            disk.build(retained, kind, output)
            prepare.assert_not_called()
        assert not any('disk_config/tools/Containerfile' in cmd for cmd in calls)
        assert ('sudo', 'podman', 'pull', '--arch', 'amd64', reference) in calls
        assert ('sudo', 'podman', 'tag', reference, metadata['update_ref']) in calls
        image_builder = next(cmd for cmd in calls if '--bootc-ref' in cmd)
        assert '--bootc-pull-container' not in image_builder
        saved = json.loads(next(output.glob('*.source.json')).read_text())
        assert saved['payload_ref'] == reference
        assert saved['update_ref'] == metadata['update_ref']
        assert saved['artifact_bytes'] == len(b'fixture image')
        assert saved['tools'] == tools
        assert '-smoke' in saved['filename']
        # Every retained-assembly command failure aborts; no package fallback.
        for index in range(len(calls)):
            failed_output = root / f'{kind}-failure-{index}'
            count = 0

            def fail(*args, capture=False):
                global count
                current = count
                count += 1
                if current == index:
                    raise subprocess.CalledProcessError(1, args)
                if '--output-name' in args:
                    name = args[args.index('--output-name') + 1]
                    (failed_output / f'{name}.{kind}').write_bytes(b'fixture')
                    return ''
                return assemble(*args, capture=capture)

            with patch.object(disk, 'run', side_effect=fail), patch.object(disk, 'prepare') as prepare:
                try:
                    disk.build(retained, kind, failed_output)
                except subprocess.CalledProcessError:
                    pass
                else:
                    raise AssertionError(f'Ignored assembly failure {index}')
                prepare.assert_not_called()
            assert not list(failed_output.glob('*.sha256'))

    # Verify config identity before tagging/running a pulled payload.
    def wrong_id(*args, capture=False):
        if '{{.Id}}' in args:
            return 'sha256:' + '0' * 64
        if args[:3] == ('sudo', 'skopeo', 'inspect'):
            return registry(*args, capture=capture)
        assert 'tag' not in args and '--entrypoint' not in args
        return ''

    with patch.object(disk, 'run', side_effect=wrong_id):
        try:
            disk.load_payload(retained)
        except ValueError:
            pass
        else:
            raise AssertionError('Ran a payload with wrong config ID')

    for mode in ('success', 'push-failed', 'bad-digest', 'changed-base-layers'):
        work = root / mode
        work.mkdir()
        pushes = []

        def publish(*args, capture=False):
            if args[:2] == ('sudo', 'cat'):
                return Path(args[2]).read_text().strip()
            if args[:3] == ('sudo', 'podman', 'push'):
                pushes.append(args)
                assert args[-2] == image_id
                assert args[-1] == f'docker://{image}-disk-payload:run-123-1-amd64'
                if mode == 'push-failed':
                    raise subprocess.CalledProcessError(1, args)
                Path(args[args.index('--digestfile') + 1]).write_text(
                    'bad' if mode == 'bad-digest' else payload_digest + '\n')
                return ''
            if mode == 'changed-base-layers' and args[-1] == f'docker://{metadata["source_ref"]}':
                return json.dumps({'layers': [{'digest': 'different', 'size': 10}]})
            return registry(*args, capture=capture)

        # A stale digest must never turn a failed push into a valid descriptor.
        (work / 'payload.digest').write_text(payload_digest)
        with patch.object(disk, 'prepare', return_value=(image_id, tools)) as prepare, patch.object(
                disk, 'run', side_effect=publish):
            if mode == 'success':
                assert disk.publish_payload(metadata, work, 'run-123-1-amd64') == retained
            else:
                try:
                    disk.publish_payload(metadata, work, 'run-123-1-amd64')
                except (ValueError, subprocess.CalledProcessError):
                    pass
                else:
                    raise AssertionError(f'Accepted {mode}')
            prepare.assert_called_once_with(metadata, work)
        assert len(pushes) == 1

    for tag in ('latest', 'run-123-1-arm64', 'run-123-1-amd64\n'):
        with patch.object(disk, 'prepare') as prepare:
            try:
                disk.publish_payload(metadata, root, tag)
            except ValueError:
                pass
            else:
                raise AssertionError(f'Accepted publication tag {tag!r}')
            prepare.assert_not_called()

with patch.object(disk, 'run', return_value=json.dumps({'Architecture': 'amd64', 'Os': 'linux'})) as commands:
    disk.preflight(metadata, 'qcow2')
    assert commands.call_count == 1
    assert commands.call_args.args[-1] == 'docker://' + metadata['builder_ref']
with patch.object(disk, 'run', return_value=json.dumps({'Architecture': 'amd64', 'Os': 'linux'})) as commands:
    disk.preflight(metadata, 'both')
    assert commands.call_count == 2
    assert 'fedora-bootc' in commands.call_args.args[-1]

with patch.object(disk, 'run', return_value=json.dumps({'Architecture': 'amd64', 'Os': 'linux'})) as commands:
    tagged = {**metadata, 'builder_ref': metadata['builder_ref'].replace('@', ':latest@')}
    disk.preflight(tagged, 'qcow2')
    assert commands.call_args.args[-1] == 'docker://' + metadata['builder_ref']
with patch.object(disk, 'run', return_value=json.dumps({'Architecture': 'arm64', 'Os': 'linux'})):

    try:
        disk.preflight(metadata, 'qcow2')
    except ValueError:
        pass
    else:
        raise AssertionError('Wrong builder platform accepted')

print('PASS retained payload identity, provenance, publication failures, digest-only reuse, both assembly formats and preflight')
