"""Exercise hard-link export with a real local OSBuild object store.

Run with python3 tests/check_vmdk_export.py; requires the osbuild Python package.
Uses sparse files above 4 GiB without a full image build or privileged mounts.
Checks allocation/content survival after store cleanup and export rejection paths.
"""

import errno
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import sys

from osbuild.objectstore import ObjectStore

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('exporter', 'scripts/export-vmdk.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


def rejected(callback):
    """Require invalid export input or a failed filesystem operation to abort."""
    try:
        callback()
    except (ValueError, OSError):
        pass
    else:
        raise AssertionError('Invalid export succeeded')


with tempfile.TemporaryDirectory(prefix='ct-export-') as temporary:
    root = Path(temporary)
    output = root / 'output'
    output.mkdir()
    destination = output / 'vmdk' / 'disk.vmdk'
    with tempfile.TemporaryDirectory(dir=output, prefix='.osbuild-store-') as cache:
        with ObjectStore(cache) as store:
            obj = store.new('a' * 64)
            source = Path(obj.tree) / 'disk.vmdk'
            size = 5 * 1024**3
            with source.open('wb') as stream:
                stream.write(b'begin')
                stream.seek(size - 3)
                stream.write(b'end')
            obj.finalize()
            manifest = {'vmdk': SimpleNamespace(id=obj.id)}
            allocated = source.stat().st_blocks
            assert allocated * 512 < size // 100
            rejected(lambda: exporter.export_vmdk('qcow2', str(output), store, manifest))
            rejected(lambda: exporter.export_vmdk('vmdk', str(output), store,
                                                  {'vmdk': SimpleNamespace(id='b' * 64)}))
            extra = Path(obj.tree) / 'unexpected'
            extra.touch()
            rejected(lambda: exporter.export_vmdk('vmdk', str(output), store, manifest))
            extra.unlink()
            saved = source.with_suffix('.saved')
            source.rename(saved)
            source.symlink_to(saved)
            # Hide the backing file outside the export tree to test the symlink itself.
            outside = root / 'backing'
            saved.rename(outside)
            source.unlink()
            source.symlink_to(outside)
            rejected(lambda: exporter.export_vmdk('vmdk', str(output), store, manifest))
            source.unlink()
            outside.rename(source)
            for code in (errno.EXDEV, errno.ENOSPC):
                with patch.object(exporter.os, 'link', side_effect=OSError(code, 'fixture')):
                    rejected(lambda: exporter.export_vmdk('vmdk', str(output), store, manifest))
                assert not destination.parent.exists()
                assert source.stat().st_nlink == 1
            exporter.export_vmdk('vmdk', str(output), store, manifest)
            assert source.samefile(destination)
            assert destination.stat().st_nlink == 2
            assert destination.stat().st_blocks == allocated
            rejected(lambda: exporter.export_vmdk('vmdk', str(output), store, manifest))
        assert destination.exists()
    assert not list(output.glob('.osbuild-store-*'))
    assert destination.stat().st_nlink == 1
    assert destination.stat().st_size == size
    assert destination.stat().st_blocks == allocated
    with destination.open('rb') as stream:
        assert stream.read(5) == b'begin'
        stream.seek(size - 3)
        assert stream.read() == b'end'

print('PASS real OSBuild store: sparse hard-link export, cleanup survival and failure boundaries')
