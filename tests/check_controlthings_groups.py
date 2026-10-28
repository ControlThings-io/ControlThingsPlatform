"""Run ``python3 tests/check_controlthings_groups.py`` on Aurora/Fedora Atomic.

Requires Bubblewrap user namespaces, NSS altfiles (/usr/lib/group), shadow-utils,
Bash, and just. Real group tools operate only on temporary account files inside
a namespace; host accounts stay untouched. The ujust check mocks pkexec, so live
desktop authorization and startup service execution remain integration checks.
"""

import os
from pathlib import Path
import subprocess
import tempfile


script = Path("system_files/usr/libexec/controlthings-groups").resolve()
recipe = Path("system_files/usr/share/ublue-os/just/60-custom.just").resolve()
assert script.stat().st_mode & 0o111
for path in (script, Path("build_files/build.sh")):
    subprocess.run(["bash", "-n", str(path)], check=True)
subprocess.run(["just", "--unstable", "--fmt", "--check", "-f", str(recipe)], check=True)

with tempfile.TemporaryDirectory(prefix="ct-groups-tests-") as temporary:
    root = Path(temporary)
    etc = root / "etc"
    etc.mkdir()
    (etc / "passwd").write_text(
        "root:x:0:0:root:/root:/bin/bash\n"
        "alpha:x:1000:1000::/home/alpha:/bin/bash\n"
        "bravo:x:1001:1001::/home/bravo:/bin/bash\n"
        "charlie:x:1002:1002::/home/charlie:/bin/bash\n"
    )
    (etc / "group").write_text(
        "root:x:0:\nwheel:x:10:alpha,bravo\n"
        "alpha:x:1000:\nbravo:x:1001:\ncharlie:x:1002:\n"
    )
    (etc / "gshadow").write_text(
        "root:!::\nwheel:!::alpha,bravo\nalpha:!::\nbravo:!::\ncharlie:!::\n"
    )
    (etc / "login.defs").write_text("SYS_GID_MIN 201\nSYS_GID_MAX 999\n")
    (etc / "nsswitch.conf").write_text(
        "passwd: files\ngroup: files [SUCCESS=merge] altfiles\nshadow: files\n"
    )
    vendor = root / "vendor-group"
    vendor.write_text("wireshark:x:900:\ndialout:x:18:\n")

    def sandbox(*args, check=True):
        """Run with read-only tools and only fixture account files writable."""
        command = [
            "bwrap", "--unshare-user", "--uid", "0", "--gid", "0",
            "--unshare-pid", "--unshare-ipc", "--unshare-uts",
            "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
            "--symlink", "usr/sbin", "/sbin", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev",
            "--bind", str(etc), "/etc", "--tmpfs", "/run", "--tmpfs", "/var",
            "--ro-bind", str(vendor), "/usr/lib/group",
            "--ro-bind", str(script), "/controlthings-groups",
        ]
        result = subprocess.run(command + list(args), text=True, capture_output=True)
        if check and result.returncode:
            raise AssertionError(f"{args}: {result.stderr}")
        return result

    def groups(user):
        return set(sandbox("id", "-nG", user).stdout.split())

    sandbox("/controlthings-groups")
    marker = etc / "ublue/controlthings-groups"
    assert marker.read_text() == "2\n"
    for user in ("alpha", "bravo"):
        assert groups(user) == {user, "wheel", "wireshark", "usbmon", "dialout"}
    assert groups("charlie") == {"charlie"}
    assert groups("root") == {"root"}
    assert sandbox("getent", "-s", "files", "group", "wireshark").stdout.split(":")[2] == "900"
    assert sandbox("getent", "-s", "files", "group", "dialout").stdout.split(":")[2] == "18"
    before = (etc / "group").read_text()
    sandbox("/controlthings-groups")
    assert (etc / "group").read_text() == before

    # Explicit setup bypasses the marker and leaves other memberships intact.
    sandbox("/controlthings-groups", "--user", "charlie")
    assert groups("charlie") == {"charlie", "wireshark", "usbmon", "dialout"}
    assert marker.read_text() == "2\n"
    before = (etc / "group").read_text()
    sandbox("/controlthings-groups", "--user", "charlie")
    assert (etc / "group").read_text() == before
    assert sandbox("/controlthings-groups", "--user", "missing", check=False).returncode != 0

    marker.unlink()
    (etc / "group").write_text(before.replace("wheel:x:10:alpha,bravo", "wheel:x:10:"))
    sandbox("/controlthings-groups")
    assert not marker.exists()
    (etc / "group").write_text(before.replace("wheel:x:10:alpha,bravo", "wheel:x:10:missing"))
    assert sandbox("/controlthings-groups", check=False).returncode != 0
    assert not marker.exists()
    (etc / "group").write_text(before)
    # Simulate version 1: capture groups were set up, but dialout was not.
    for user in ("alpha", "bravo"):
        sandbox("gpasswd", "--delete", user, "dialout")
        assert groups(user) == {user, "wheel", "wireshark", "usbmon"}
    marker.write_text("1\n")
    sandbox("/controlthings-groups")
    assert marker.read_text() == "2\n"
    for user in ("alpha", "bravo"):
        assert groups(user) == {user, "wheel", "wireshark", "usbmon", "dialout"}
    assert groups("charlie") == {"charlie", "wireshark", "usbmon", "dialout"}

    # Verify the real recipe delegates only the current user to the shared script.
    mock_bin = root / "bin"
    mock_bin.mkdir()
    mock = mock_bin / "pkexec"
    capture = root / "pkexec-args"
    mock.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CAPTURE_ARGS"\n')
    mock.chmod(0o755)
    env = dict(os.environ, PATH=str(mock_bin) + os.pathsep + os.environ["PATH"],
               CAPTURE_ARGS=str(capture))
    subprocess.run(["just", "-f", str(recipe), "controlthings-groups"], env=env,
                   capture_output=True, text=True, check=True)
    username = subprocess.check_output(["id", "-un"], text=True).strip()
    assert capture.read_text().splitlines() == ["/usr/libexec/controlthings-groups", "--user", username]

print("PASS real group tools: all wheel users, manual user, preserved memberships/vendor GID,")
print("     marker skip/upgrade, empty wheel retry, failure handling; ujust delegation and syntax")
