"""Check disk selection/orchestration with ``python3 tests/check_build_disk.py``.

Requires Python 3.10+, PyYAML and 7zz; runs without registry access or root.
Mocks container/registry commands and uses real 7z packaging, exercising
real resolution, file naming, checksums, failure propagation, and workflow shell
syntax. Does not establish image-builder, Anaconda, or VM integration success.
"""

import hashlib
import itertools
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

from disk_test_fixtures import assembly_command

spec = importlib.util.spec_from_file_location("build_disk", "scripts/build-disk.py")
disk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(disk)
digest = "sha256:" + "a" * 64
amd_digest = "sha256:" + "b" * 64
payload_id = "sha256:" + "d" * 64
for value in (payload_id, payload_id.removeprefix("sha256:"),
              "348b624b76c0081b9ff003d42b0351b3a3f2c531561e19f692d1833174f9df33"):
    assert disk.canonical_image_id(value) == "sha256:" + value.removeprefix("sha256:")
for value in ("", "d" * 12, "d" * 63, "d" * 65, "g" * 64,
              "sha512:" + "d" * 64, "sha256:sha256:" + "d" * 64,
              "d" * 64 + "\n"):
    try:
        disk.canonical_image_id(value)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Invalid image ID accepted: {value!r}")
image = "ghcr.io/controlthings-io/controlthingsplatform"
builder = "ghcr.io/osbuild/image-builder@sha256:" + "c" * 64
assert disk.workflow_suffix({}) == ""
assert disk.workflow_suffix({'workflow_run': '123', 'workflow_attempt': '2'}) == '-123-2'
for run_id, attempt in (('123/path', '1'), ('123', '2\n'), ('123', '-1')):
    try:
        disk.workflow_suffix({'workflow_run': run_id, 'workflow_attempt': attempt})
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid artifact suffix accepted')
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
        for kind in ("iso", "qcow2", "vmdk"):
            if kind == "vmdk" and architecture == "arm64":
                continue
            for channel in ("latest", "ics410_l01", "ics410-l01"):
                metadata = resolve(channel, architecture=architecture)
                if kind == "qcow2":
                    metadata.update(workflow_run="12345", workflow_attempt="2")
                output = Path(temporary) / f"{kind}-{channel}-{architecture}"
                commands = []

                def command(*args, capture=False):
                    commands.append(args)
                    response = assembly_command(args)
                    if response is not None:
                        return response
                    # Rootful Podman's storage directory is inaccessible to
                    # the runner account, even for a read-only df diagnostic.
                    if args[0] == "df" and "/var/lib/containers/storage" in args:
                        raise subprocess.CalledProcessError(1, args, stderr="Permission denied")
                    if args[:4] == ("sudo", "podman", "image", "inspect"):
                        if "{{.Id}}" in args:
                            # Ubuntu's Podman returns bare IDs; other versions
                            # include the sha256 prefix. Both must be accepted.
                            return payload_id.removeprefix("sha256:") if kind == "qcow2" else payload_id
                        return digest
                    if "--entrypoint" in args:
                        return json.dumps({"architecture": disk.ARCHITECTURES[architecture],
                                           "profile": "controlthings" if channel == "latest" else "full",
                                           "homebrew_versions": ["fixture 1.0"],
                                           "manifests_sha256": {"controlthings.Brewfile": "e" * 64,
                                                                "system-flatpaks.Brewfile": "f" * 64},
                                           "flatpak": ["org.mozilla.firefox", "dk.gqrx.gqrx"],
                                           "flatpak_commits": {"fixture": "f" * 64}})
                    if "--output-name" in args:
                        basename = args[args.index("--output-name") + 1]
                        (output / f"{basename}.{kind}").write_bytes(b"fixture disk contents")
                    return ""

                with patch.object(disk, "run", side_effect=command):
                    disk.build(metadata, kind, output)
                if kind == "iso":
                    iso_command_count = len(commands)
                name = f"controlthingsplatform-{channel}-20261015-5118339-{architecture}"
                if kind == "iso":
                    name += "-installer"
                elif kind == "qcow2":
                    name += "-12345-2"
                artifact = output / f"{name}.{kind}"
                assert artifact.exists()
                assert artifact.with_suffix(artifact.suffix + ".sha256").read_text() == (
                    f'{hashlib.sha256(artifact.read_bytes()).hexdigest()}  {artifact.name}\n'
                )
                saved = json.loads((output / f"{name}.source.json").read_text())
                assert saved["format"] == kind
                assert saved["artifact_bytes"] == artifact.stat().st_size
                assert not any(cmd[:2] == ("qemu-img", "convert") for cmd in commands)
                if kind == "vmdk":
                    assert saved["vmdk_subformat"] == "monolithicSparse"
                    runner = next(cmd for cmd in commands if '/run-ct-osbuild.sh' in cmd)
                    assert str(Path('scripts/export-vmdk.py').resolve()) + ':/run-ct-export.py:ro' in runner
                    assert saved["bundle_filename"].endswith(".7z")
                    assert (output / saved["bundle_filename"]).is_file()
                    assert not list(output.glob(".bundle-*"))
                else:
                    assert "vmdk_subformat" not in saved
                assert saved["source_digest"] == digest
                assert saved["disk_payload_image_id"] == payload_id
                assert saved["tools"]["homebrew_versions"] == ["fixture 1.0"]
                assert "org.mozilla.firefox" in saved["tools"]["flatpak"]
                assert "system-flatpaks.Brewfile" in saved["tools"]["manifests_sha256"]
                assert saved["update_ref"] == f"{image}:{channel}"
                assert commands[0] == ("sudo", "podman", "pull", "--arch", architecture, f"{image}@{digest}")
                assert commands[1] == ("sudo", "podman", "tag", f"{image}@{digest}", f"{image}:{channel}")
                payload_build = next(cmd for cmd in commands if "disk_config/tools/Containerfile" in cmd)
                assert f"BASE_IMAGE={image}@{digest}" in payload_build
                assert payload_build[payload_build.index("--arch") + 1] == architecture
                assert "--pull=never" in payload_build and "--no-cache" in payload_build
                assert payload_build[payload_build.index("--tag") + 1] == f"{image}:{channel}"
                assert "--cap-add" in payload_build and "SYS_ADMIN" in payload_build
                assert "NET_ADMIN" in payload_build
                build_id_arg = next(arg for arg in payload_build if arg.startswith("DISK_BUILD_ID="))
                build_id = build_id_arg.split("=", 1)[1]
                assert len(build_id) == 32 and all(c in "0123456789abcdef" for c in build_id)
                cleanup = next(cmd for cmd in commands if "prune" in cmd)
                diagnostics = [cmd for cmd in commands if "df" in cmd and "-h" in cmd]
                assert diagnostics == [("sudo", "df", "-h", str(output),
                                        "/var/lib/containers/storage")] * 2
                assert cleanup == ("sudo", "podman", "image", "prune", "--force", "--filter",
                                   f"label=io.controlthings.disk-build={build_id}")
                assert commands.index(cleanup) > commands.index(payload_build)
                assert commands.index(cleanup) < commands.index(next(
                    cmd for cmd in commands if "--bootc-ref" in cmd))
                invocation = next(cmd for cmd in commands if "--bootc-ref" in cmd)
                assert "--bootc-pull-container" not in invocation
                assert invocation[invocation.index("manifest" if kind == "vmdk" else "build") + 1] == (
                    "bootc-generic-iso" if kind == "iso" else kind
                )
                assert invocation[invocation.index("--arch") + 1] == ("x86_64" if architecture == "amd64" else "aarch64")
                assert saved["architecture"] == architecture
                if kind == "iso":
                    installer_build = next(cmd for cmd in commands if "disk_config/installer/Containerfile" in cmd)
                    assert installer_build[installer_build.index("--arch") + 1] == architecture
                    assert f"TARGET_ARCH={architecture}" in installer_build
                    assert invocation[invocation.index("--bootc-installer-payload-ref") + 1] == f"{image}:{channel}"
                else:
                    assert invocation[invocation.index("--bootc-ref") + 1] == f"{image}:{channel}"
                    assert invocation[invocation.index("--image-size") + 1] == "64 GiB"

    # Every external build stage must abort before checksums appear on failure.
    metadata = resolve("latest")
    for fail_at in range(iso_command_count):
        output = Path(temporary) / f"failure-{fail_at}"
        calls = []

        def failing(*args, capture=False):
            calls.append(args)
            if len(calls) - 1 == fail_at:
                raise subprocess.CalledProcessError(1, args)
            if "--entrypoint" in args:
                return json.dumps({"architecture": "x86_64"})
            if "--output-name" in args:
                basename = args[args.index("--output-name") + 1]
                (output / f"{basename}.iso").write_bytes(b"fixture disk contents")
            return digest if capture else ""

        try:
            with patch.object(disk, "run", side_effect=failing):
                disk.build(metadata, "iso", output)
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError("Command failure was ignored")
        assert not list(output.glob("*.sha256"))
    for mode in ("wrong-digest", "invalid-payload-id", "wrong-tool-arch", "missing-output"):
        output = Path(temporary) / mode

        def invalid_build(*args, capture=False):
            if "{{.Digest}}" in args:
                return "wrong" if mode == "wrong-digest" else digest
            if "{{.Id}}" in args:
                return "wrong" if mode == "invalid-payload-id" else payload_id
            if "--entrypoint" in args:
                return json.dumps({"architecture": "aarch64" if mode == "wrong-tool-arch" else "x86_64"})
            return ""

        try:
            with patch.object(disk, "run", side_effect=invalid_build):
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
inputs = workflow[True]["workflow_dispatch"]["inputs"]
assert "format" not in inputs
for kind in disk.FORMATS:
    assert inputs[kind]["type"] == "boolean"
    assert inputs[kind]["default"] == (kind == "qcow2")
assert workflow["jobs"]["build"]["strategy"]["matrix"]["format"] == (
    '${{ fromJSON(needs.resolve.outputs.formats) }}')
assert workflow["jobs"]["resolve"]["outputs"]["formats"] == '${{ steps.formats.outputs.formats }}'
selection_step = next(step for step in workflow["jobs"]["resolve"]["steps"]
                      if step.get("id") == "formats")
# Execute the real workflow shell for every checkbox combination on each arch.
with tempfile.TemporaryDirectory(prefix="ct-formats-") as temporary:
    github_output = Path(temporary) / "outputs"
    for architecture in disk.ARCHITECTURES:
        for flags in itertools.product((False, True), repeat=3):
            selected = [kind for kind, enabled in zip(disk.FORMATS, flags) if enabled]
            github_output.write_text("")
            env = dict(os.environ, TARGET_ARCH=architecture, GITHUB_OUTPUT=str(github_output))
            env.update({f"BUILD_{kind.upper()}": str(enabled).lower()
                        for kind, enabled in zip(disk.FORMATS, flags)})
            result = subprocess.run(['bash', '-e', '-c', selection_step['run']],
                                    env=env, text=True, capture_output=True)
            valid = bool(selected) and not (architecture == "arm64" and "vmdk" in selected)
            assert (result.returncode == 0) == valid, result.stderr
            if valid:
                assert json.loads(result.stdout) == selected
                assert json.loads(github_output.read_text().removeprefix("formats=")) == selected
            else:
                assert not github_output.read_text()

# Invalid targets must fail before registry calls, preparation or output creation.
for kinds, architecture in (([], "amd64"), (["vmdk"], "arm64"), (["raw"], "amd64")):
    with patch.object(disk, "run") as command:
        try:
            disk.preflight({"architecture": architecture}, kinds)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid preflight selection accepted")
        command.assert_not_called()
with patch.object(disk, "prepare") as prepare:
    try:
        disk.build({"architecture": "arm64"}, "vmdk", Path("unused-output"))
    except ValueError:
        pass
    else:
        raise AssertionError("ARM64 Workstation disk accepted")
    prepare.assert_not_called()

assert workflow["jobs"]["build"]["needs"] == ["resolve", "prepare"]
assert workflow["jobs"]["prepare"]["needs"] == "resolve"
assert workflow["jobs"]["prepare"]["permissions"]["packages"] == "write"
assert workflow["permissions"]["packages"] == "read"
assert "payload_ref" in workflow[True]["workflow_dispatch"]["inputs"]
# Successful job outputs survive re-run-failed-jobs; using the new run_attempt
# directly in downloads would request an artifact that was never uploaded.
for job_name, dependency in (("prepare", "resolve"), ("build", "prepare")):
    download = next(step for step in workflow["jobs"][job_name]["steps"]
                    if step.get("uses", "").startswith("actions/download-artifact@"))
    assert download["with"]["name"] == "${{ needs." + dependency + ".outputs.artifact_name }}"
assembly = next(step for step in workflow["jobs"]["build"]["steps"]
                if step["name"] == "Assemble retained payload and checksum")
assert "build disk-input/prepared.json" in assembly["run"]

uploads = [step for step in workflow['jobs']['build']['steps']
           if step.get('uses', '').startswith('actions/upload-artifact@')]
assert len(uploads) == 4
bundle_upload = next(step for step in uploads if step['with']['path'] == 'output/*.7z')
assert bundle_upload['with']['archive'] is False
assert bundle_upload['if'] == "matrix.format == 'vmdk'"
qcow_upload = next(step for step in uploads if step['with']['path'] == 'output/*.qcow2')
assert qcow_upload['if'] == "matrix.format == 'qcow2'"
assert qcow_upload['with']['archive'] is False
metadata_upload = next(step for step in uploads if 'metadata-' in step['with'].get('name', ''))
assert metadata_upload['with']['path'].splitlines() == ['output/*.json', 'output/*.sha256']
assert metadata_upload['if'] == "matrix.format != 'iso'"
assert '${{ matrix.format }}-metadata-' in metadata_upload['with']['name']
assert metadata_upload['with'].get('archive', True) is True
assert uploads[0]['if'] == "matrix.format == 'iso'"
assert uploads[0]['with']['path'] == 'output/'
assert uploads[0]['with']['compression-level'] == 0
build_tools = next(step for step in workflow['jobs']['build']['steps']
                   if step['name'] == 'Install disk build tools')
assert '7zip' in build_tools['run']

# Exercise S3 filters without installation or network access.
s3 = next(step for step in workflow['jobs']['build']['steps'] if step['name'] == 'Upload to S3')
with tempfile.TemporaryDirectory(prefix='ct-upload-') as temporary:
    root = Path(temporary)
    (root / 'sudo').write_text('#!/bin/sh\nexit 0\n')
    (root / 'sudo').chmod(0o755)
    (root / 'rclone').write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$UPLOAD_CAPTURE"\n')
    (root / 'rclone').chmod(0o755)
    for kind in disk.FORMATS:
        capture = root / kind
        env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'],
                   UPLOAD_CAPTURE=str(capture), DISK_FORMAT=kind, S3_BUCKET='fixture',
                   SOURCE_TAG='latest-20261020-abcdef0', GITHUB_RUN_ID='123',
                   GITHUB_RUN_ATTEMPT='2', TARGET_ARCH='amd64')
        subprocess.run(['bash', '-e', '-c', s3['run']], env=env, check=True)
        args = capture.read_text().splitlines()
        assert args[:3] == ['copy', 'output/', f'S3:fixture/latest-20261020-abcdef0/123-2/amd64/{kind}/']
        assert args[3:] == (['--include', '*.7z', '--include', '*.json', '--include', '*.sha256']
                            if kind == 'vmdk' else [])

for job in workflow["jobs"].values():
    for step in job["steps"]:
        if "run" in step:
            subprocess.run(["bash", "-n"], input=step["run"], text=True, check=True)
        if "uses" in step:
            assert len(step["uses"].split("@")[-1]) == 40
installer = Path("disk_config/installer/Containerfile").read_text()
assert "containers-storage:%s --target-imgref %s" in installer
assert "org.fedoraproject.Anaconda.Modules.Subscription" not in installer
tools_container = Path("disk_config/tools/Containerfile").read_text()
assert 'FROM ${BASE_IMAGE}' in tools_container
assert 'COPY --chown=1000:1000 --from=tools-builder /var/home/linuxbrew /var/home/linuxbrew' in tools_container
assert 'COPY --from=tools-builder /var/lib/flatpak /var/lib/flatpak' in tools_container
assert 'controlthings.Brewfile' not in '\n'.join(
    line for line in tools_container.splitlines() if line.startswith('COPY'))
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
print("PASS disk tag selection, immutable metadata, AMD64/ARM64 manifest selection, all formats/channels,")
print("     disk-only stores/identity, checksums/metadata, failures, native runners, installer packages and workflow syntax")
