#!/usr/bin/python3
"""Run OSBuild with a single-file, hard-link VMDK export.

Installed as the container's OSBuild entrypoint by run-osbuild.sh. Keep the
standard CLI's validation, dependency selection, build and error handling, but
replace its export callback to avoid the full disk copy that exhausted CI space.
This adapter depends on osbuild.main_cli.export(name, output, store, manifest)
and ObjectStore.get()/Object.tree; review it when updating the builder pin.
The runner owns a disposable store on the output filesystem and removes it
after the CLI exits, before the host changes UUIDs, hashes or compresses the disk.
"""

import os
from pathlib import Path
import shutil
import stat

from osbuild import main_cli
from osbuild.objectstore import ObjectStore
from osbuild.pipeline import Manifest


def export_vmdk(name: str, output: str, store: ObjectStore, manifest: Manifest) -> None:
    """Link the sole regular VMDK into a new export directory, without copying.

    Reject other exports, extra entries, symlinks and existing destinations.
    Cross-filesystem links fail rather than silently falling back to a large
    copy. The store retains its original file until normal cleanup; the output
    link survives that cleanup with identical bytes and sparse allocation.
    """
    if name != "vmdk":
        raise ValueError("Only the vmdk pipeline may use hard-link export")
    obj = store.get(manifest[name].id)
    if obj is None:
        raise ValueError("Missing completed VMDK object")
    entries = list(Path(obj.tree).iterdir())
    if len(entries) != 1 or entries[0].suffix != ".vmdk":
        raise ValueError("Expected exactly one VMDK in the export tree")
    source = entries[0]
    info = source.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size == 0:
        raise ValueError("Expected a nonempty regular VMDK")
    destination = Path(output) / name
    print(f"VMDK export: {info.st_size} logical bytes, "
          f"{info.st_blocks * 512} allocated bytes, "
          f"{shutil.disk_usage(output).free} output bytes free", flush=True)
    destination.mkdir()
    try:
        os.link(source, destination / source.name, follow_symlinks=False)
    except OSError:
        destination.rmdir()
        raise


if __name__ == "__main__":
    main_cli.export = export_vmdk
    raise SystemExit(main_cli.osbuild_cli())
