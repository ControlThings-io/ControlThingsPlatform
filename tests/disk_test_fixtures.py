"""Small command fixtures for disk orchestration; no real OSBuild or guest boot."""

import json
from pathlib import Path
import struct

CAPACITY = 8 * 1024 * 1024


def vmdk_manifest():
    """Mirror the relevant pipeline structure in the pinned builder's manifest."""
    return {"version": "2", "pipelines": [
        {"name": "image", "stages": [{"type": "org.osbuild.truncate", "options": {
            "filename": "disk.raw", "size": str(CAPACITY)}}]},
        {"name": "vmdk", "stages": [{"type": "org.osbuild.qemu", "inputs": {"image": {
            "type": "org.osbuild.files", "origin": "org.osbuild.pipeline",
            "references": {"name:image": {"file": "disk.raw"}}}}, "options": {
                "filename": "disk.vmdk", "format": {"type": "vmdk", "subformat": "streamOptimized"}}}]},
    ]}


def sparse_fixture(path):
    """Write just enough header/descriptor for media UUID tests, not a usable disk."""
    header = bytearray(512)
    header[:4] = b"KDMV"
    struct.pack_into("<QQ", header, 28, 1, 20)
    descriptor = f'# Disk DescriptorFile\ncreateType="monolithicSparse"\nRW 16384 SPARSE "{path.name}"\n'
    path.write_bytes(header + descriptor.encode().ljust(20 * 512, b"\0") + b"fixture sectors")


def assembly_command(args):
    """Return mocked builder/inspection output, or None for unrelated commands."""
    if args[:2] == ("qemu-img", "info"):
        return json.dumps({"format": "vmdk", "virtual-size": CAPACITY,
                           "format-specific": {"data": {"create-type": "monolithicSparse",
                            "extents": [{"filename": args[-1], "compressed": False}]}}})
    if "manifest" in args and "--bootc-ref" in args:
        return json.dumps(vmdk_manifest())
    if "/run-ct-osbuild.sh" in args:
        output = Path(next(a.removesuffix(":/output") for a in args if a.endswith(":/output")))
        manifest = json.loads((output / Path(args[-1]).name).read_text())
        stage = next(p for p in manifest["pipelines"] if p["name"] == "vmdk")["stages"][0]
        assert stage["options"]["format"] == {
            "type": "vmdk", "subformat": "monolithicSparse", "compression": False}
        target = output / "vmdk" / stage["options"]["filename"]
        target.parent.mkdir()
        sparse_fixture(target)
        return ""
    return None
