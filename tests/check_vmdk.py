"""Check direct VMDK output, media UUIDs and compressed VM bundles.

Run from the repository root with python3 tests/check_vmdk.py. Requires qemu-img,
qemu-io and 7zz. Uses a real local OSBuild QEMU stage when installed, otherwise QEMU
with its documented stage arguments. This is small-disk validation, not OSBuild
container integration or VMware/VirtualBox boot validation.
"""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import struct
import subprocess
import sys
import tempfile
from unittest.mock import patch
import uuid
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

from disk_test_fixtures import vmdk_manifest
spec = importlib.util.spec_from_file_location('disk', 'scripts/build-disk.py')
disk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(disk)


def rejected(callback):
    """Require a malformed input to fail closed."""
    try:
        callback()
    except (ValueError, subprocess.CalledProcessError):
        pass
    else:
        raise AssertionError('Invalid input accepted')


manifest = vmdk_manifest()
original = copy.deepcopy(manifest)
capacity = disk.configure_vmdk_manifest(manifest, 'versioned.vmdk')
assert manifest['pipelines'][0] == original['pipelines'][0]
options = manifest['pipelines'][1]['stages'][0]['options']
assert options == {'filename': 'versioned.vmdk', 'format': {
    'type': 'vmdk', 'subformat': 'monolithicSparse', 'compression': False}}
for change in ('missing', 'duplicate', 'extra-stage', 'input', 'capacity', 'format'):
    invalid = copy.deepcopy(original)
    if change == 'missing':
        invalid['pipelines'].pop()
    elif change == 'duplicate':
        invalid['pipelines'].append(copy.deepcopy(invalid['pipelines'][1]))
    elif change == 'extra-stage':
        invalid['pipelines'][1]['stages'].append({'type': 'unexpected'})
    elif change == 'input':
        invalid['pipelines'][1]['stages'][0]['inputs']['image']['references'] = {}
    elif change == 'capacity':
        invalid['pipelines'][0]['stages'][0]['options']['size'] = '0'
    else:
        invalid['pipelines'][1]['stages'][0]['options']['format']['type'] = 'qcow2'
    rejected(lambda: disk.configure_vmdk_manifest(invalid, 'disk.vmdk'))
for name in ('../disk.vmdk', 'disk".vmdk', 'disk\n.vmdk', '/disk.vmdk'):
    rejected(lambda: disk.configure_vmdk_manifest(copy.deepcopy(original), name))

ns = {'v': 'http://www.virtualbox.org/'}
template_dir = Path('disk_config/virtualization')
templates_before = {p.name: p.read_bytes() for p in template_dir.iterdir()}
with tempfile.TemporaryDirectory(prefix='ct-vmdk-') as temporary:
    root = Path(temporary)
    raw = root / 'disk.raw'
    with raw.open('wb') as stream:
        stream.truncate(capacity)
        for offset in (0, 65536, 7 * 1024 * 1024):
            stream.seek(offset)
            stream.write(bytes(range(256)) * 16)
    artifact = root / options['filename']
    stage = Path('/usr/lib/osbuild/stages/org.osbuild.qemu')
    if stage.exists():
        implementation = runpy.run_path(str(stage))
        assert implementation['main']({'image': {'path': str(root), 'data': {
            'files': {'disk.raw': {}}}}}, str(root), options) == 0
        print('PASS real local OSBuild QEMU stage: raw -> monolithicSparse')
    else:
        subprocess.run(['qemu-img', 'convert', '-f', 'raw', '-O', 'vmdk',
                        '-o', 'subformat=monolithicSparse', str(raw), str(artifact)], check=True)
        print('Local OSBuild stage unavailable; tested equivalent QEMU invocation')
    disk.validate_vmdk(artifact, capacity)
    rejected(lambda: disk.validate_vmdk(artifact, capacity + 512))
    original_disk = artifact.read_bytes()
    original_info = json.loads(subprocess.check_output(
        ['qemu-img', 'info', '--output=json', str(artifact)], text=True))
    for mode in ('format', 'capacity', 'subformat', 'compressed', 'external', 'split'):
        bad = copy.deepcopy(original_info)
        details = bad['format-specific']['data']
        if mode == 'format':
            bad['format'] = 'qcow2'
        elif mode == 'capacity':
            bad['virtual-size'] = 0
        elif mode == 'subformat':
            details['create-type'] = 'streamOptimized'
        elif mode == 'compressed':
            details['extents'][0]['compressed'] = True
        elif mode == 'external':
            details['extents'][0]['filename'] = str(root / 'other.vmdk')
        else:
            details['extents'].append(copy.deepcopy(details['extents'][0]))
        with patch.object(disk, 'run', return_value=json.dumps(bad)):
            rejected(lambda: disk.validate_vmdk(artifact, capacity))

    media_uuid = disk.vmdk_media_uuid(artifact)
    assert uuid.UUID(media_uuid).version == 4
    after_uuid = artifact.read_bytes()
    assert disk.vmdk_media_uuid(artifact) == media_uuid
    assert artifact.read_bytes() == after_uuid
    descriptor_offset, sectors = struct.unpack_from('<QQ', original_disk, 28)
    assert after_uuid[:descriptor_offset * 512] == original_disk[:descriptor_offset * 512]
    assert after_uuid[(descriptor_offset + sectors) * 512:] == original_disk[(descriptor_offset + sectors) * 512:]
    disk.validate_vmdk(artifact, capacity)
    subprocess.run(['qemu-img', 'compare', '-f', 'raw', '-F', 'vmdk',
                    str(raw), str(artifact)], check=True)

    machine_ids = set()
    for channel in ('latest', 'latest', 'ics410_l01', 'ics410-l01'):
        metadata = {'source_tag': f'{channel}-20261020-abcdef0',
                    'workflow_run': '12345', 'workflow_attempt': str(len(machine_ids) + 1)}
        bundle = disk.package_vmdk(artifact, metadata)
        assert bundle.name.endswith(f'-vmdk-12345-{metadata["workflow_attempt"]}.7z')
        subprocess.run(['7zz', 't', str(bundle)], check=True, stdout=subprocess.DEVNULL)
        details = subprocess.check_output(['7zz', 'l', '-slt', str(bundle)], text=True)
        assert 'Type = 7z' in details and 'Method = LZMA2' in details
        assert 'Solid = -' in details
        with tempfile.TemporaryDirectory(dir=root) as extracted:
            subprocess.run(['7zz', 'x', str(bundle), f'-o{extracted}'],
                           check=True, stdout=subprocess.DEVNULL)
            members = Path(extracted)
            expected = {artifact.name, 'controlthingsplatform.vmx'}
            if channel == 'latest':
                expected.add('controlthingsplatform.vbox')
            assert {p.name for p in members.iterdir()} == expected
            assert (members / artifact.name).read_bytes() == artifact.read_bytes()
            vmx = (members / 'controlthingsplatform.vmx').read_bytes().decode()
            display = ('ControlThings Platform' if channel == 'latest' else
                       f'{channel.upper()} - ControlThings Platform')
            assert f'displayName = "{display}"' in vmx
            assert f'nvme0:0.fileName = "{artifact.name}"' in vmx
            assert 'numvcpus = "2"' in vmx and 'cpuid.coresPerSocket = "2"' in vmx
            # Only the approved fields differ, including preservation of CRLF.
            original_vmx = templates_before['controlthingsplatform.vmx'].decode()
            assert vmx == original_vmx.replace('displayName = "ControlThings Platform"',
                                               f'displayName = "{display}"').replace(
                'nvme0:0.fileName = "controlthingsplatform.vmdk"', f'nvme0:0.fileName = "{artifact.name}"')
            if channel == 'latest':
                vbox_bytes = (members / 'controlthingsplatform.vbox').read_bytes()
                vbox = ET.fromstring(vbox_bytes)
                machine = vbox.find('v:Machine', ns)
                machine_id = machine.get('uuid')
                assert machine_id not in machine_ids
                machine_ids.add(machine_id)
                hard_disk = machine.find('v:MediaRegistry/v:HardDisks/v:HardDisk', ns)
                attached = machine.find('.//v:AttachedDevice/v:Image', ns)
                assert hard_disk.get('uuid') == attached.get('uuid') == '{' + media_uuid + '}'
                assert hard_disk.get('location') == artifact.name
                old = ET.fromstring(templates_before['controlthingsplatform.vbox'])
                old_machine = old.find('v:Machine', ns)
                old_disk = old_machine.find('v:MediaRegistry/v:HardDisks/v:HardDisk', ns)
                expected_vbox = templates_before['controlthingsplatform.vbox'].decode().replace(
                    f'<Machine uuid="{old_machine.get("uuid")}"', f'<Machine uuid="{machine_id}"').replace(
                    f'uuid="{old_disk.get("uuid")}"', f'uuid="{{{media_uuid}}}"').replace(
                    'location="controlthingsplatform.vmdk"', f'location="{artifact.name}"')
                assert vbox_bytes == expected_vbox.encode()
        assert bundle.stat().st_size < artifact.stat().st_size
        disk.write_checksum(artifact)
        disk.write_checksum(bundle)
        for path in (artifact, bundle):
            assert path.with_name(path.name + '.sha256').read_text() == (
                hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n')
        bundle.unlink()
    # Missing tools and compression failures must leave no publishable archive,
    # temporary directory or staged hard-link; the source disk remains intact.
    for error in (FileNotFoundError('7zz'), subprocess.CalledProcessError(2, ['7zz'])):
        def failed_compression(args, **kwargs):
            Path(args[args.index('--') - 1]).write_bytes(b'partial archive')
            raise error

        with patch.object(disk.subprocess, 'run', side_effect=failed_compression):
            try:
                disk.package_vmdk(artifact, {'source_tag': 'latest'})
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass
            else:
                raise AssertionError('Ignored packaging failure')
        assert not list(root.glob('*.7z')) and not list(root.glob('.bundle-*'))
        assert artifact.read_bytes() == after_uuid
        assert artifact.stat().st_nlink == 1

    # Descriptor validation rejects malformed bounds/data without changing bytes.
    for mode in ('magic', 'bounds', 'padding', 'duplicate', 'invalid-uuid', 'full'):
        invalid = bytearray(original_disk)
        if mode == 'magic':
            invalid[:4] = b'nope'
        elif mode == 'bounds':
            struct.pack_into('<Q', invalid, 36, 100000)
        elif mode == 'padding':
            invalid[1023] = 1
        else:
            text = original_disk[512:512 + sectors * 512].split(b'\0')[0]
            if mode == 'duplicate':
                text += f'ddb.uuid.image = "{media_uuid}"\n'.encode() * 2
            elif mode == 'invalid-uuid':
                text += b'ddb.uuid.image = "broken"\n'
            else:
                text += b'#' * (sectors * 512 - len(text) - 1)
            invalid[512:512 + sectors * 512] = text.ljust(sectors * 512, b'\0')
        artifact.write_bytes(invalid)
        rejected(lambda: disk.vmdk_media_uuid(artifact))
        assert artifact.read_bytes() == invalid
    artifact.write_bytes(after_uuid)
    subprocess.run(['qemu-io', '-f', 'vmdk', '-c', 'write -P 0x5a 1048576 4096',
                    str(artifact)], check=True)
    subprocess.run(['qemu-io', '-r', '-f', 'vmdk', '-c', 'read -P 0x5a 1048576 4096',
                    str(artifact)], check=True)

assert templates_before == {p.name: p.read_bytes() for p in template_dir.iterdir()}
print('PASS direct VMDK format/content/write, UUID preservation, channel bundles, checksums and failures')
