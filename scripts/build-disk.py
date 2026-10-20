#!/usr/bin/env python3
"""Resolve and build disk inputs with moving update channels on native runners.

Usage: build-disk.py resolve IMAGE TAG BUILDER OUTPUT_JSON [--arch {amd64,arm64}]
       build-disk.py build INPUT_JSON {iso,qcow2,vmdk} OUTPUT_DIR
       build-disk.py prepare INPUT_JSON OUTPUT_JSON --tag run-RUNID-ATTEMPT-ARCH
       build-disk.py reuse INPUT_JSON PAYLOAD_DIGEST_REF OUTPUT_JSON
       build-disk.py preflight INPUT_JSON {iso,qcow2,vmdk,both} [...]
       build-disk.py formats --arch ARCH --qcow2 BOOL --iso BOOL --vmdk BOOL

Requires Skopeo for resolution and sudo/Podman for builds. Resolution inspects
immutable metadata after selecting a digest; all selected jobs consume that JSON.
Preparation populates a disk-only image's /var with Homebrew and Flatpaks.
CI retains it in a separate registry package, then assembly pulls that digest
and gives it the channel name in local storage. The OS and
tool manifest come from the selected digest; app versions resolve at disk-build
time. image-builder uses local storage, and future updates follow the original
published OS channel. Assembly failures leave the retained payload available;
final disk artifacts are uploaded only after successful assembly.
"""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid

ARCHITECTURES = {"amd64": "x86_64", "arm64": "aarch64"}
FORMATS = ("qcow2", "iso", "vmdk")


def validate_formats(kinds: list[str], architecture: str) -> None:
    """Reject empty/unknown selections and ARM64 VMDK before payload work.

    VMDK targets VMware Workstation on AMD64; ARM64 remains available for ISO
    and QCOW2. This validates our supported targets, not builder capabilities.
    """
    if architecture not in ARCHITECTURES:
        raise ValueError("Architecture must be amd64 or arm64")
    if not kinds or any(kind not in FORMATS for kind in kinds):
        raise ValueError("Select at least one output: qcow2, iso, or vmdk")
    if "vmdk" in kinds and architecture != "amd64":
        raise ValueError("VMDK targets VMware Workstation and requires amd64")


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


LABEL_PREFIX = "io.controlthings.disk."
TOOLS_CONTEXT = Path(__file__).resolve().parents[1] / "disk_config/tools"


def recipe_digest() -> str:
    """Hash preparation inputs; source digest already covers its helper/manifest.

    Include names and separators so different file boundaries cannot collide.
    Assembly-script changes do not invalidate an already prepared payload.
    """
    digest = hashlib.sha256()
    for name in ("Containerfile", "build-tools.sh"):
        digest.update(name.encode() + b"\0")
        digest.update((TOOLS_CONTEXT / name).read_bytes() + b"\0")
    return digest.hexdigest()


def payload_labels(metadata: dict[str, str]) -> dict[str, str]:
    """Return the immutable provenance required to reuse a prepared image."""
    return {LABEL_PREFIX + "source": metadata["source_ref"],
            LABEL_PREFIX + "recipe": recipe_digest(),
            LABEL_PREFIX + "channel": metadata["update_ref"]}


def payload_repository(metadata: dict[str, str]) -> str:
    """Keep disk caches in a distinct GHCR package, never in OS channel tags."""
    return metadata["image"] + "-disk-payload"


def validate_payload_config(metadata: dict[str, str], config: dict) -> None:
    """Reject mismatched platform/provenance before any payload is executed."""
    if config.get("architecture") != metadata["architecture"] or config.get("os") != "linux":
        raise ValueError("Retained payload has the wrong OS/architecture")
    labels = config.get("config", {}).get("Labels", {})
    for key, expected in payload_labels(metadata).items():
        if labels.get(key) != expected:
            raise ValueError(f"Retained payload mismatch: {key}; prepare a fresh payload")


def reuse_payload(metadata: dict[str, str], reference: str) -> dict[str, str]:
    """Validate a same-project digest reference using metadata-only registry reads.

    No application data is downloaded. Reject moving tags, foreign repositories,
    changed source/channel/recipe, multiarch indexes, and invalid image identities.
    Returns source metadata extended with the immutable payload identity.
    Requires Skopeo and root's registry login for private cache packages.
    """
    pattern = re.escape(payload_repository(metadata)) + r"@sha256:[a-f0-9]{64}"
    if not re.fullmatch(pattern, reference):
        raise ValueError("Use a digest reference from this project's -disk-payload package")
    raw = run("sudo", "skopeo", "inspect", "--raw", f"docker://{reference}", capture=True)
    manifest = json.loads(raw)
    if "manifests" in manifest or "config" not in manifest or "layers" not in manifest:
        raise ValueError("Expected a single-platform payload manifest")
    config_id = canonical_image_id(manifest["config"]["digest"])
    config = json.loads(run("sudo", "skopeo", "inspect", "--config",
                            f"docker://{reference}", capture=True))
    validate_payload_config(metadata, config)
    return {**metadata, "payload_ref": reference, "payload_image_id": config_id,
            "payload_recipe_sha256": recipe_digest(),
            "payload_layer_bytes": str(sum(layer["size"] for layer in manifest["layers"]))}


def publish_payload(metadata: dict[str, str], work: Path, tag: str) -> dict[str, str]:
    """Prepare once and push a uniquely named cache image, returning its digest.

    Tag must be run-RUNID-ATTEMPT-ARCH; destination is always the separate cache
    package. Only a successful push plus registry validation yields metadata.
    No archive is written. Registry retention is manual; do not delete payloads
    still referenced by disk runs. Root must already be logged into GHCR.
    """
    if not re.fullmatch(r"run-[0-9]+-[0-9]+-" + metadata["architecture"], tag):
        raise ValueError("Payload tag must be run-RUNID-ATTEMPT-ARCH")
    payload_id, _ = prepare(metadata, work)
    digest_file = work.resolve() / "payload.digest"
    # Avoid consuming an old digest if a push is interrupted or fails.
    digest_file.unlink(missing_ok=True)
    destination = f"{payload_repository(metadata)}:{tag}"
    run("sudo", "podman", "push", "--digestfile", str(digest_file),
        payload_id, f"docker://{destination}")
    # Push runs as root; read through sudo even under a restrictive root umask.
    digest = run("sudo", "cat", str(digest_file), capture=True)
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("Push did not produce a valid payload manifest digest")
    retained = reuse_payload(metadata, f"{payload_repository(metadata)}@{digest}")
    if retained["payload_image_id"] != payload_id:
        raise ValueError("Published payload config changed during transport")
    source_manifest = json.loads(run("sudo", "skopeo", "inspect", "--raw",
                                     f'docker://{metadata["source_ref"]}', capture=True))
    payload_manifest = json.loads(run("sudo", "skopeo", "inspect", "--raw",
                                      f'docker://{retained["payload_ref"]}', capture=True))
    base_layers = [layer["digest"] for layer in source_manifest["layers"]]
    prepared_layers = [layer["digest"] for layer in payload_manifest["layers"]]
    if prepared_layers[:len(base_layers)] != base_layers:
        raise ValueError("Published payload did not preserve the base OS layer digests")
    return retained


def load_payload(metadata: dict[str, str]) -> tuple[str, dict]:
    """Pull/verify a retained image and locally tag it with the normal OS channel.

    Validate provenance before running its metadata reader. The expected config
    ID protects identity across publication/pull. Failure never falls back to
    downloading and installing fresh applications.
    """
    retained = reuse_payload(metadata, metadata["payload_ref"])
    if retained["payload_image_id"] != metadata.get("payload_image_id"):
        raise ValueError("Retained payload identity disagrees with preparation metadata")
    reference = retained["payload_ref"]
    run("sudo", "podman", "pull", "--arch", metadata["architecture"], reference)
    payload_id = canonical_image_id(run("sudo", "podman", "image", "inspect", "--format",
                                       "{{.Id}}", reference, capture=True))
    if payload_id != retained["payload_image_id"]:
        raise ValueError("Pulled payload has the wrong image config ID")
    run("sudo", "podman", "tag", reference, metadata["update_ref"])
    tools = json.loads(run("sudo", "podman", "run", "--rm", "--entrypoint", "cat", reference,
                          "/var/lib/controlthings/tools/installed.json", capture=True))
    if tools["architecture"] != ARCHITECTURES[metadata["architecture"]]:
        raise ValueError("Retained payload tool metadata has the wrong architecture")
    return payload_id, tools


def preflight(metadata: dict[str, str], kinds: str | list[str]) -> None:
    """Check builder/installer availability before expensive application work.

    Checks only registry metadata, not layer downloads or runner capacity.
    Accept one format or a list; legacy "both" expands to ISO plus QCOW2.
    ISO uses the pinned FROM reference in our installer Containerfile.
    """
    # Retain the legacy CLI's "both" alias for ISO plus QCOW2.
    if isinstance(kinds, str):
        kinds = [kinds]
    if "both" in kinds:
        kinds = [kind for kind in kinds if kind != "both"] + ["iso", "qcow2"]
    validate_formats(kinds, metadata["architecture"])
    refs = [metadata["builder_ref"]]
    if "iso" in kinds:
        installer = TOOLS_CONTEXT.parent / "installer/Containerfile"
        refs.append(next(line.split()[1] for line in installer.read_text().splitlines()
                         if line.startswith("FROM ")))
    for reference in refs:
        # Podman accepts tag@digest pins, but Skopeo's docker transport does not.
        # Preserve the immutable digest while dropping only a trailing tag.
        repository, separator, digest = reference.partition("@")
        if separator:
            reference = re.sub(r":[^/]+$", "", repository) + "@" + digest
        info = json.loads(run("skopeo", "inspect", "--override-arch", metadata["architecture"],
                              "--no-tags", f"docker://{reference}", capture=True))
        if info.get("Architecture") != metadata["architecture"] or info.get("Os") != "linux":
            raise ValueError(f"Build dependency lacks linux/{metadata['architecture']}: {reference}")


def prepare(metadata: dict[str, str], work: Path) -> tuple[str, dict]:
    """Populate and validate one local payload, then release its builder stages.

    Requires the selected source manifest/helper and native Podman. Returns the
    image config ID and installed-tool metadata. The payload receives only a
    local channel tag; publication, if requested, is a separate operation.
    """
    architecture = metadata["architecture"]
    if architecture not in ARCHITECTURES:
        raise ValueError("Architecture must be amd64 or arm64")
    work.mkdir(parents=True, exist_ok=True)
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
    build_id = uuid.uuid4().hex
    run("sudo", "podman", "build", "--arch", architecture, "--pull=never", "--no-cache",
        "--cap-add", "SYS_ADMIN", "--cap-add", "NET_ADMIN",
        "--security-opt", "label=disable",
        "--build-arg", f"BASE_IMAGE={source}",
        "--build-arg", f"DISK_BUILD_ID={build_id}",
        "--build-arg", f"PAYLOAD_RECIPE={recipe_digest()}",
        "--build-arg", f"UPDATE_REF={channel}",
        "--build-arg", "SOURCE_REPOSITORY=https://github.com/" + metadata["image"].removeprefix("ghcr.io/"),
        "--tag", channel,
        "--file", "disk_config/tools/Containerfile", "disk_config/tools")
    payload_id = canonical_image_id(run(
        "sudo", "podman", "image", "inspect", "--format",
        "{{.Id}}", channel, capture=True))
    tools = json.loads(run("sudo", "podman", "run", "--rm", "--entrypoint", "cat", channel,
                          "/var/lib/controlthings/tools/installed.json", capture=True))
    if tools["architecture"] != ARCHITECTURES[architecture]:
        raise ValueError("Disk tool payload has the wrong architecture")
    # COPY leaves the populated tools-builder image in local storage. Release
    # its duplicate stores before osbuild imports another copy of the payload.
    # This invocation's label exists only on that disposable stage; keep the
    # tagged payload, its ancestors and every unrelated image untouched.
    # Rootful Podman's storage directory requires root even for statfs/df.
    run("sudo", "df", "-h", str(work), "/var/lib/containers/storage")
    run("sudo", "podman", "image", "prune", "--force", "--filter",
        f"label=io.controlthings.disk-build={build_id}")
    run("sudo", "podman", "system", "df")
    run("sudo", "df", "-h", str(work), "/var/lib/containers/storage")
    return payload_id, tools


def build(metadata: dict[str, str], kind: str, output: Path) -> None:
    """Assemble a disk and emit checksums/provenance into an empty directory.

    A retained payload is pulled by digest and validated when payload_ref is set;
    otherwise the local CLI prepares one. Assembly always uses the original OS
    channel tag locally, so installed systems update from the normal OS channel.
    No application installers run when consuming a retained payload.
    """
    architecture = metadata["architecture"]
    validate_formats([kind], architecture)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Output directory must be empty")
    channel = metadata["update_ref"]
    if metadata.get("payload_ref"):
        payload_id, tools = load_payload(metadata)
    else:
        payload_id, tools = prepare(metadata, output)
    image_type, bootc_ref = kind, channel
    name = f'{metadata["image"].rsplit("/", 1)[-1]}-{metadata["source_tag"]}-{architecture}'
    # Preserve accurate filenames when assembling retained historical smoke payloads.
    # Current ControlThings bundles use the standard name without a smoke suffix.
    if tools.get("profile") == "smoke":
        name += "-smoke"
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
                    "disk_payload_image_id": payload_id, "artifact_bytes": artifact.stat().st_size,
                    "tools": tools}, indent=2) + "\n"
    )


def main() -> None:
    """Dispatch resolution, preparation/reuse, preflight and local disk assembly."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    selection = commands.add_parser("resolve")
    for argument in ("image", "tag", "builder", "output"):
        selection.add_argument(argument)
    selection.add_argument("--arch", choices=ARCHITECTURES, default="amd64")
    disk = commands.add_parser("build")
    disk.add_argument("metadata", type=Path)
    disk.add_argument("kind", choices=FORMATS)
    disk.add_argument("output", type=Path)
    preparation = commands.add_parser("prepare")
    preparation.add_argument("metadata", type=Path)
    preparation.add_argument("output", type=Path)
    preparation.add_argument("--tag", required=True)
    reuse = commands.add_parser("reuse")
    reuse.add_argument("metadata", type=Path)
    reuse.add_argument("reference")
    reuse.add_argument("output", type=Path)
    check = commands.add_parser("preflight")
    check.add_argument("metadata", type=Path)
    check.add_argument("kind", nargs="+", choices=(*FORMATS, "both"))
    formats = commands.add_parser("formats", help="Validate checkboxes and emit a JSON matrix")
    formats.add_argument("--arch", choices=ARCHITECTURES, default="amd64")
    for kind in FORMATS:
        formats.add_argument(f"--{kind}", choices=("true", "false"), required=True)
    args = parser.parse_args()
    if args.command == "formats":
        kinds = [kind for kind in FORMATS if getattr(args, kind) == "true"]
        validate_formats(kinds, args.arch)
        matrix = json.dumps(kinds)
        print(matrix)
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
                stream.write(f"formats={matrix}\n")
        return
    if args.command == "resolve":
        metadata = resolve(args.image, args.tag, args.builder, args.arch)
        Path(args.output).write_text(json.dumps(metadata, indent=2) + "\n")
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
                stream.write(f'source_tag={metadata["source_tag"]}\n')
    else:
        metadata = json.loads(args.metadata.read_text())
        if args.command == "build":
            build(metadata, args.kind, args.output)
        elif args.command == "preflight":
            preflight(metadata, args.kind)
        else:
            if args.output.exists():
                raise ValueError("Prepared metadata output already exists")
            if args.command == "prepare":
                metadata = publish_payload(metadata, args.output.parent, args.tag)
            else:
                metadata = reuse_payload(metadata, args.reference)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
