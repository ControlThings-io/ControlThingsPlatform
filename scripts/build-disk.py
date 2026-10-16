#!/usr/bin/env python3
"""Resolve and build disk inputs with moving update channels on native runners.

Usage: build-disk.py resolve IMAGE TAG BUILDER OUTPUT_JSON [--arch {amd64,arm64}]
       build-disk.py build INPUT_JSON {iso,qcow2} OUTPUT_DIR

Requires Skopeo for resolution and sudo/Podman for builds. Resolution inspects
immutable metadata after selecting a digest; both matrix jobs consume that JSON.
Builds pull only that digest, populate a disposable disk-only image's /var with
Homebrew and Flatpaks, then give it the channel name in local storage. The OS and
tool manifest come from the selected digest; app versions resolve at disk-build
time. image-builder uses local storage, and future updates follow the original
published OS channel. Errors abort without upload.
"""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ARCHITECTURES = {"amd64": "x86_64", "arm64": "aarch64"}


def run(*args: str, capture: bool = False) -> str:
    """Run a command; stream build logs or capture metadata, and propagate errors."""
    result = subprocess.run(args, text=True, check=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""


def canonical_image_id(value: str) -> str:
    """Return a sha256-prefixed ID from Podman's bare or prefixed full ID.

    Podman versions differ in inspect's .Id presentation. Reject abbreviated,
    malformed and non-SHA256 IDs; metadata always records the canonical form.
    """
    match = re.fullmatch(r"(?:sha256:)?([a-f0-9]{64})", value)
    if not match:
        raise ValueError("Disk payload has an invalid local image ID")
    return f"sha256:{match[1]}"


def channel_for(tag: str) -> str:
    """Accept channel or fully dated tags; preserve course hyphens/underscores."""
    match = re.fullmatch(
        r"(latest|ics410[-_][a-z0-9]+)(?:-(\d{8})-([a-f0-9]{7,40}))?", tag
    )
    if not match:
        raise ValueError("Use latest, ics410_l01/ics410-l01, or CHANNEL-YYYYMMDD-HASH")
    return match[1]


def resolve(image: str, tag: str, builder: str,
            architecture: str = "amd64") -> dict[str, str]:
    """Return verified source identity and a date/hash name from container labels.

    Reject missing build labels, wrong architecture, invalid dates, and dated
    tags inconsistent with the actual image. Never substitute workflow HEAD or
    the disk build date. OCI revision may belong to the base image, so the
    project's version label supplies the source hash instead.
    """
    if architecture not in ARCHITECTURES:
        raise ValueError("Architecture must be amd64 or arm64")
    image, tag = image.lower(), tag.lower()
    channel = channel_for(tag)
    digest = run("skopeo", "inspect", "--override-arch", architecture, "--format",
                 "{{.Digest}}", f"docker://{image}:{tag}", capture=True)
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("Registry returned an invalid source digest")
    manifest = json.loads(run("skopeo", "inspect", "--raw",
                              f"docker://{image}@{digest}", capture=True))
    if "manifests" in manifest:
        matches = [entry["digest"] for entry in manifest["manifests"]
                   if entry.get("platform", {}).get("architecture") == architecture
                   and entry.get("platform", {}).get("os") == "linux"]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one linux/{architecture} image in manifest list")
        digest = matches[0]
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
            raise ValueError(f"Invalid {architecture} manifest digest")
    source_ref = f"{image}@{digest}"
    info = json.loads(run("skopeo", "inspect", "--override-arch", architecture,
                          "--no-tags", f"docker://{source_ref}", capture=True))
    if info["Architecture"] != architecture or info["Os"] != "linux":
        raise ValueError(f"Selected tag requires a published linux/{architecture} source image; "
                         f"found {info['Os']}/{info['Architecture']}")
    version = info.get("Labels", {}).get("org.opencontainers.image.version", "")
    match = re.fullmatch(r".+[.-](\d{8})-([a-f0-9]{7,40})", version)
    if not match:
        raise ValueError("Container version label must include YYYYMMDD-HASH")
    date, commit = match.groups()
    datetime.strptime(date, "%Y%m%d")
    source_tag = f"{channel}-{date}-{commit}"
    if tag != channel and tag != source_tag:
        raise ValueError("Requested dated tag disagrees with container version label")
    return {
        "image": image, "requested_tag": tag, "source_ref": source_ref,
        "source_digest": digest, "source_tag": source_tag,
        "container_version": version, "container_created": info["Created"],
        "container_commit": commit, "architecture": architecture,
        "update_channel": channel, "update_ref": f"{image}:{channel}",
        "builder_ref": builder,
        "workflow_run": os.environ.get("GITHUB_RUN_ID", ""),
        "workflow_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
    }


def build(metadata: dict[str, str], kind: str, output: Path) -> None:
    """Build one format, then emit SHA256 and source metadata beside its image.

    Output must be absent or empty. ISO embeds a local payload and sets its
    update reference explicitly in Anaconda; QCOW2 inherits its local tag as
    target-imgref. Prepare app stores in a disk-only derivative of the verified
    source; never publish it. Record its image ID and app versions separately
    from the original source digest. No remote-source option or channel pull is
    allowed here. Missing manifest/helper in an older source fails the build.
    """
    architecture = metadata["architecture"]
    if architecture not in ARCHITECTURES:
        raise ValueError("Architecture must be amd64 or arm64")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Output directory must be empty")
    source, channel = metadata["source_ref"], metadata["update_ref"]
    run("sudo", "podman", "pull", "--arch", architecture, source)
    run("sudo", "podman", "tag", source, channel)
    local_digest = run("sudo", "podman", "image", "inspect", "--format",
                       "{{.Digest}}", channel, capture=True)
    if local_digest != metadata["source_digest"]:
        raise ValueError("Local channel does not match the resolved payload digest")
    # Only the manual disk workflow invokes this nested-sandbox-capable stage.
    # Retag locally with the original channel so installed updates keep following
    # the published, lean OS image rather than the disposable derivative.
    run("sudo", "podman", "build", "--arch", architecture, "--pull=never", "--no-cache",
        "--cap-add", "SYS_ADMIN", "--cap-add", "NET_ADMIN",
        "--security-opt", "label=disable",
        "--build-arg", f"BASE_IMAGE={source}", "--tag", channel,
        "--file", "disk_config/tools/Containerfile", "disk_config/tools")
    payload_id = canonical_image_id(run(
        "sudo", "podman", "image", "inspect", "--format",
        "{{.Id}}", channel, capture=True))
    tools = json.loads(run("sudo", "podman", "run", "--rm", "--entrypoint", "cat", channel,
                          "/var/lib/controlthings/tools/installed.json", capture=True))
    if tools["architecture"] != ARCHITECTURES[architecture]:
        raise ValueError("Disk tool payload has the wrong architecture")
    image_type, bootc_ref = "qcow2", channel
    name = f'{metadata["image"].rsplit("/", 1)[-1]}-{metadata["source_tag"]}-{architecture}'
    extra = []
    if kind == "iso":
        image_type, bootc_ref = "bootc-generic-iso", "localhost/controlthings-installer:build"
        name += "-installer"
        run("sudo", "podman", "build", "--arch", architecture, "--pull=missing",
            "--build-arg", f"TARGET_ARCH={architecture}",
            "--build-arg", f"PAYLOAD_REF={channel}", "--tag", bootc_ref,
            "--file", "disk_config/installer/Containerfile", "disk_config/installer")
        extra = ["--bootc-installer-payload-ref", channel]
    else:
        # For bootc disks --image-size sets a root minimum before boot partitions.
        extra = ["--image-size", "64 GiB"]
    run("sudo", "podman", "run", "--rm", "--privileged",
        "--security-opt", "label=type:unconfined_t",
        "-v", f"{output}:/output",
        "-v", "/var/lib/containers/storage:/var/lib/containers/storage",
        metadata["builder_ref"], "build", image_type, "--arch", ARCHITECTURES[architecture],
        "--bootc-ref", bootc_ref, "--bootc-default-fs", "btrfs",
        "--output-dir", "/output", "--output-name", name,
        "--with-manifest", *extra)
    run("sudo", "chown", "-R", f"{os.getuid()}:{os.getgid()}", str(output))
    artifact = output / f"{name}.{kind}"
    if not artifact.is_file() or artifact.stat().st_size == 0:
        raise ValueError(f"Builder did not produce {artifact.name}")
    # Stream large disk images rather than retaining their contents in memory.
    checksum = hashlib.sha256()
    with artifact.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    (output / f"{artifact.name}.sha256").write_text(
        f"{checksum.hexdigest()}  {artifact.name}\n"
    )
    (output / f"{name}.source.json").write_text(
        json.dumps({**metadata, "format": kind, "filename": artifact.name,
                    "disk_payload_image_id": payload_id, "tools": tools}, indent=2) + "\n"
    )


def main() -> None:
    """Dispatch resolve/build; write only trusted generated fields to Actions outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    selection = commands.add_parser("resolve")
    for argument in ("image", "tag", "builder", "output"):
        selection.add_argument(argument)
    selection.add_argument("--arch", choices=ARCHITECTURES, default="amd64")
    disk = commands.add_parser("build")
    disk.add_argument("metadata", type=Path)
    disk.add_argument("kind", choices=("iso", "qcow2"))
    disk.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "resolve":
        metadata = resolve(args.image, args.tag, args.builder, args.arch)
        Path(args.output).write_text(json.dumps(metadata, indent=2) + "\n")
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
                stream.write(f'source_tag={metadata["source_tag"]}\n')
    else:
        build(json.loads(args.metadata.read_text()), args.kind, args.output)


if __name__ == "__main__":
    main()
