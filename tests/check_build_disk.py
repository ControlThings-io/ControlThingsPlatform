"""Check disk selection/orchestration with ``python3 tests/check_build_disk.py``.

Requires Python 3.9+ and PyYAML; runs without registry access or root.
Mocks only external commands, exercising
real resolution, file naming, checksums, failure propagation, and workflow shell
syntax. Does not establish image-builder, Anaconda, or VM integration success.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

import yaml

sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location("build_disk", "scripts/build-disk.py")
disk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(disk)
digest = "sha256:" + "a" * 64
amd_digest = "sha256:" + "b" * 64
image = "ghcr.io/controlthings-io/controlthingsplatform"
builder = "ghcr.io/osbuild/image-builder@sha256:" + "c" * 64
info = {
    "Architecture": "amd64", "Os": "linux", "Created": "2026-10-15T19:22:11Z",
    # Actual project course builds may inherit the latest prefix. Only date/hash
    # come from this label; the requested tag determines the update channel.
    "Labels": {"org.opencontainers.image.version": "latest.20261015-5118339"},
}


def resolve(tag, *, manifest=None, metadata=None, architecture="amd64"):
    """Resolve a fixture and assert metadata is fetched by immutable reference."""
    responses = [digest, json.dumps(manifest or {}), json.dumps(metadata or {**info, "Architecture": architecture})]
    with patch.object(disk, "run", side_effect=responses) as command:
        result = disk.resolve(image, tag, builder, architecture)
        assert command.call_args_list[-1].args[-1] == f'docker://{result["source_ref"]}'
        assert result["architecture"] == architecture
        assert command.call_args_list[0].args[command.call_args_list[0].args.index("--override-arch") + 1] == architecture
        return result


for channel in ("latest", "ics410_l01", "ics410-l01"):
    for tag in (channel, f"{channel}-20261015-5118339"):
        metadata = resolve(tag)
        assert metadata["update_ref"] == f"{image}:{channel}"
        assert metadata["source_tag"] == f"{channel}-20261015-5118339"
        assert metadata["container_commit"] == "5118339"
for invalid in ("main", "pr-12", "latest;echo", "../latest", "latest\nfoo",
                "latest-20261015", "ics410_l01-5118339"):
    try:
        disk.channel_for(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(invalid)
for tag, metadata in (
    ("latest-20261015-abcdef0", info),
    ("latest", {**info, "Architecture": "arm64"}),
    ("latest", {**info, "Os": "windows"}),
    ("latest", {**info, "Labels": {}}),
    ("latest", {**info, "Labels": {"org.opencontainers.image.version": "latest.20260230-5118339"}}),
):
    try:
        resolve(tag, metadata=metadata)
    except ValueError:
        pass
    else:
        raise AssertionError((tag, metadata))
multiarch = {"manifests": [
    {"digest": amd_digest, "platform": {"architecture": "amd64", "os": "linux"}},
    {"digest": digest, "platform": {"architecture": "arm64", "os": "linux"}},
]}
assert resolve("latest", manifest=multiarch)["source_digest"] == amd_digest
try:
    resolve("latest", manifest={"manifests": [multiarch["manifests"][1]]})
except ValueError:
    pass
else:
    raise AssertionError("Missing AMD64 image accepted")

assert resolve("latest", manifest=multiarch, architecture="arm64")["source_digest"] == digest
for architecture, metadata, manifest in (
    ("arm64", info, {}),
    ("amd64", {**info, "Architecture": "arm64"}, {}),
    ("arm64", {**info, "Architecture": "arm64"}, {"manifests": [multiarch["manifests"][0]]}),
    ("riscv64", info, {}),
):
    try:
        resolve("latest", architecture=architecture, metadata=metadata, manifest=manifest)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Missing/invalid architecture accepted: {architecture}")

with tempfile.TemporaryDirectory(prefix="ct-disk-tests-") as temporary:
    for architecture in ("amd64", "arm64"):
        for kind in ("iso", "qcow2"):
            for channel in ("latest", "ics410_l01", "ics410-l01"):
                metadata = resolve(channel, architecture=architecture)
                output = Path(temporary) / f"{kind}-{channel}-{architecture}"
                commands = []

                def command(*args, capture=False):
                    commands.append(args)
                    if args[:4] == ("sudo", "podman", "image", "inspect"):
                        return digest
                    if args[:3] == ("sudo", "podman", "run"):
                        basename = args[args.index("--output-name") + 1]
                        (output / f"{basename}.{kind}").write_bytes(b"fixture disk contents")
                    return ""

                with patch.object(disk, "run", side_effect=command):
                    disk.build(metadata, kind, output)
                name = f"controlthingsplatform-{channel}-20261015-5118339-{architecture}"
                if kind == "iso":
                    name += "-installer"
                artifact = output / f"{name}.{kind}"
                assert artifact.exists()
                assert artifact.with_suffix(artifact.suffix + ".sha256").read_text() == (
                    f'{hashlib.sha256(artifact.read_bytes()).hexdigest()}  {artifact.name}\n'
                )
                saved = json.loads((output / f"{name}.source.json").read_text())
                assert saved["source_digest"] == digest
                assert saved["update_ref"] == f"{image}:{channel}"
                assert commands[0] == ("sudo", "podman", "pull", "--arch", architecture, f"{image}@{digest}")
                assert commands[1] == ("sudo", "podman", "tag", f"{image}@{digest}", f"{image}:{channel}")
                invocation = next(cmd for cmd in commands if cmd[:3] == ("sudo", "podman", "run"))
                assert "--bootc-pull-container" not in invocation
                assert invocation[invocation.index("build") + 1] == (
                    "bootc-generic-iso" if kind == "iso" else "qcow2"
                )
                assert invocation[invocation.index("--arch") + 1] == ("x86_64" if architecture == "amd64" else "aarch64")
                assert saved["architecture"] == architecture
                if kind == "iso":
                    installer_build = next(cmd for cmd in commands if cmd[:3] == ("sudo", "podman", "build"))
                    assert installer_build[installer_build.index("--arch") + 1] == architecture
                    assert f"TARGET_ARCH={architecture}" in installer_build
                    assert invocation[invocation.index("--bootc-installer-payload-ref") + 1] == f"{image}:{channel}"
                else:
                    assert invocation[invocation.index("--bootc-ref") + 1] == f"{image}:{channel}"
                    assert invocation[invocation.index("--image-size") + 1] == "20 GiB"

    # A pull/tag/inspection/builder failure must abort before checksums appear.
    metadata = resolve("latest")
    for fail_at in range(5):
        output = Path(temporary) / f"failure-{fail_at}"
        calls = []

        def failing(*args, capture=False):
            calls.append(args)
            if len(calls) - 1 == fail_at:
                raise subprocess.CalledProcessError(1, args)
            return digest if capture else ""

        try:
            with patch.object(disk, "run", side_effect=failing):
                disk.build(metadata, "iso", output)
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError("Command failure was ignored")
        assert not list(output.glob("*.sha256"))
    for mode in ("wrong-digest", "missing-output"):
        output = Path(temporary) / mode
        try:
            with patch.object(disk, "run", return_value="wrong" if mode == "wrong-digest" else digest):
                disk.build(metadata, "qcow2", output)
        except ValueError:
            pass
        else:
            raise AssertionError(mode)
        assert not list(output.glob("*.sha256"))

workflow = yaml.safe_load(Path(".github/workflows/build-disk.yml").read_text())
assert set(workflow[True]) == {"workflow_dispatch"}  # PyYAML YAML 1.1 parses 'on' as True.
platform = workflow[True]["workflow_dispatch"]["inputs"]["platform"]
assert platform["type"] == "choice" and platform["options"] == ["amd64", "arm64"]
assert platform["default"] == "amd64"
assert workflow["jobs"]["resolve"]["runs-on"] == "ubuntu-24.04"
runner = workflow["jobs"]["build"]["runs-on"]
assert runner == "${{ inputs.platform == 'arm64' && 'ubuntu-24.04-arm' || 'ubuntu-24.04' }}"
assert "${{ inputs.platform }}" in workflow["concurrency"]["group"]
assert workflow["jobs"]["build"]["strategy"]["matrix"]["format"] == ["iso", "qcow2"]
assert workflow["jobs"]["build"]["needs"] == "resolve"
for job in workflow["jobs"].values():
    for step in job["steps"]:
        if "run" in step:
            subprocess.run(["bash", "-n"], input=step["run"], text=True, check=True)
        if "uses" in step:
            assert len(step["uses"].split("@")[-1]) == 40
installer = Path("disk_config/installer/Containerfile").read_text()
assert "containers-storage:%s --target-imgref %s" in installer
assert "org.fedoraproject.Anaconda.Modules.Subscription" not in installer
# Execute the actual installer package-selection RUN block with a mocked DNF.
package_step = installer.split("RUN case ", 1)[1].split("\n\n", 1)[0]
package_step = "case " + package_step
with tempfile.TemporaryDirectory(prefix="ct-installer-packages-") as temporary:
    mock = Path(temporary) / "dnf"
    mock.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$CAPTURE_PACKAGES"\n')
    mock.chmod(0o755)
    for architecture, efi in (("amd64", "grub2-efi-x64-cdboot"),
                              ("arm64", "grub2-efi-aa64-cdboot")):
        capture = Path(temporary) / architecture
        env = dict(os.environ, TARGET_ARCH=architecture,
                   PATH=temporary + os.pathsep + os.environ["PATH"],
                   CAPTURE_PACKAGES=str(capture))
        subprocess.run(["bash", "-e", "-c", package_step], env=env, check=True)
        packages = capture.read_text().splitlines()
        assert efi in packages
        assert ("grub2-pc-modules" in packages) == (architecture == "amd64")
        assert ("grub2-efi-x64-cdboot" in packages) == (architecture == "amd64")
        assert ("grub2-efi-aa64-cdboot" in packages) == (architecture == "arm64")
print("PASS disk tag selection, immutable metadata, AMD64/ARM64 manifest selection, both formats/channels,")
print("     checksums/metadata, failures, native runners, installer packages, pins, workflow shell syntax")
