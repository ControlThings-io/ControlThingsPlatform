"""Check new-user groups with real Fedora account tools in a private filesystem.

Run ``python3 tests/check_controlthings_groups.py``. Requires Bubblewrap, unshare
with subordinate UID/GID mappings, NSS altfiles, shadow-utils, KDE config tools,
Bash, Python and just.
Only temporary account/config files are writable; host accounts are untouched.
Exercise the image configurator, Plasma Setup's useradd/usermod sequence and
this branch's actual workbook and Homebrew account commands.
The graphical wizard, KAuth and deployed bootc /etc merges still need VM checks.
"""

from pathlib import Path
import shlex
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "build_files/configure-user-groups.sh"
TARGET_GROUPS = {"wireshark", "usbmon", "dialout", "plugdev"}
build = (ROOT / "build_files/build.sh").read_text()
assert build.index('install "${PACKAGES[@]}"') < build.index(
    "bash /ctx/configure-user-groups.sh") < build.index("/usr/libexec/uv-tools setup")
assert "controlthings-groups" not in build
for relative in ("system_files/usr/libexec/controlthings-groups",
                 "system_files/usr/lib/systemd/system/controlthings-groups.service"):
    assert not (ROOT / relative).exists()
recipe = ROOT / "system_files/usr/share/ublue-os/just/60-custom.just"
assert "controlthings-groups" not in recipe.read_text()
for path in (SCRIPT, ROOT / "build_files/build.sh"):
    subprocess.run(["bash", "-n", str(path)], check=True)
subprocess.run(["just", "--unstable", "--fmt", "--check", "-f", str(recipe)], check=True)

with tempfile.TemporaryDirectory(prefix="ct-groups-tests-") as temporary:
    root = Path(temporary)
    etc = root / "etc"
    (etc / "default").mkdir(parents=True)
    (etc / "xdg").mkdir()
    (etc / "passwd").write_text(
        "root:x:0:0:root:/root:/bin/bash\n"
        "existing:x:1000:1000::/home/existing:/bin/bash\n")
    (etc / "group").write_text(
        "root:x:0:\nwheel:x:10:existing\nexisting:x:1000:\n"
        "plugdev:x:480:existing\nextra:x:481:\n")
    (etc / "gshadow").write_text(
        "root:!::\nwheel:!::existing\nexisting:!::\n"
        "plugdev:!::existing\nextra:!::\n")
    (etc / "shadow").write_text("root:!*:1::::::\nexisting:!*:1::::::\n")
    (etc / "login.defs").write_text(
        "UID_MIN 1000\nUID_MAX 60000\nSYS_UID_MIN 201\nSYS_UID_MAX 999\n"
        "SYS_GID_MIN 201\nSYS_GID_MAX 999\nUSERGROUPS_ENAB yes\n")
    (etc / "nsswitch.conf").write_text(
        "passwd: files\ngroup: files [SUCCESS=merge] altfiles\nshadow: files\n")
    defaults = etc / "default/useradd"
    defaults.write_text(
        "# Inherited defaults\nGROUP=100\nHOME=/home\nSHELL=/bin/bash\n"
        "SKEL=/etc/skel\nCREATE_MAIL_SPOOL=no\nGROUPS=extra\nGROUPS=extra\n")
    plasma = etc / "xdg/plasmasetuprc"
    plasma.write_text("# Inherited KDE settings\n[Accounts]\nUserGroups=wheel\n"
                      "[Other]\nKeep=unchanged\n")
    vendor = root / "vendor-group"
    vendor.write_text("wireshark:x:900:\ndialout:x:18:\nplugdev:x:46:\n")

    def sandbox(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run real tools with only fixture accounts/config writable."""
        command = [
            "unshare", "--user", "--map-auto", "--map-root-user", "bwrap",
            "--unshare-pid", "--unshare-net", "--unshare-ipc", "--unshare-uts",
            "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
            "--symlink", "usr/sbin", "/sbin", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev",
            "--bind", str(etc), "/etc", "--tmpfs", "/run", "--tmpfs", "/var",
            "--tmpfs", "/home", "--tmpfs", "/tmp",
            "--setenv", "XDG_CONFIG_HOME", "/tmp/config",
            "--ro-bind", str(vendor), "/usr/lib/group",
            "--ro-bind", str(SCRIPT), "/configure-user-groups.sh",
        ]
        result = subprocess.run(command + list(args), text=True, capture_output=True)
        if check and result.returncode:
            raise AssertionError(f"{args}: {result.stdout}\n{result.stderr}")
        return result

    def groups(user: str) -> set[str]:
        """Read stored memberships without a login or boot service."""
        return set(sandbox("id", "-nG", user).stdout.split())

    before = {name: (etc / name).read_bytes() for name in ("passwd", "shadow")}
    sandbox("bash", "/configure-user-groups.sh")
    assert groups("existing") == {"existing", "wheel", "plugdev"}
    assert all((etc / name).read_bytes() == content for name, content in before.items())
    for group, gid in (("wireshark", "900"), ("dialout", "18"), ("plugdev", "480")):
        assert sandbox("getent", "-s", "files", "group", group).stdout.split(":")[2] == gid
    assert sandbox("getent", "-s", "files", "group", "usbmon").stdout
    assert defaults.read_text().count("GROUPS=") == 1
    assert "HOME=/home\nSHELL=/bin/bash\nSKEL=/etc/skel\n" in defaults.read_text()
    assert "GROUP=100\n" in defaults.read_text()
    assert "GROUPS=wireshark,usbmon,dialout,plugdev\n" in defaults.read_text()
    kde_groups = sandbox("kreadconfig6", "--file", "/etc/xdg/plasmasetuprc",
                         "--group", "Accounts", "--key", "UserGroups").stdout.strip()
    assert set(kde_groups.split(",")) == TARGET_GROUPS | {"wheel"}
    assert sandbox("kreadconfig6", "--file", "/etc/xdg/plasmasetuprc",
                   "--group", "Other", "--key", "Keep").stdout.strip() == "unchanged"

    # Aurora normally ships no GROUPS key; this path must also add the defaults.
    defaults.write_text("\n".join(line for line in defaults.read_text().splitlines()
                                   if not line.startswith("GROUPS=")) + "\n")
    sandbox("bash", "/configure-user-groups.sh")
    assert "GROUPS=wireshark,usbmon,dialout,plugdev\n" in defaults.read_text()

    # Reapplying image configuration must preserve account data and defaults.
    paths = ("group", "gshadow", "default/useradd", "xdg/plasmasetuprc")
    snapshot = {name: (etc / name).read_bytes() for name in paths}
    sandbox("bash", "/configure-user-groups.sh")
    assert all((etc / name).read_bytes() == data for name, data in snapshot.items())

    # Normal users get defaults before wheel membership exists, with no retries.
    sandbox("useradd", "--no-log-init", "--no-create-home", "--user-group", "student")
    assert groups("student") == {"student"} | TARGET_GROUPS
    assert "wheel" not in groups("student")
    # The first administrator follows Plasma Setup 6.7.5's creation sequence.
    sandbox("useradd", "--no-log-init", "--create-home", "--user-group", "first")
    sandbox("usermod", "--append", "--groups", kde_groups, "first")
    assert groups("first") == {"first", "wheel"} | TARGET_GROUPS
    # A process initializing its groups immediately sees them on its first run.
    for user in ("student", "first"):
        effective = sandbox("setpriv", "--reuid", user, "--regid", user,
                            "--init-groups", "--", "id", "-nG").stdout.split()
        assert set(effective) == groups(user)
    # The KDE setting works independently when useradd defaults are overridden.
    sandbox("useradd", "--no-log-init", "--no-create-home", "--user-group",
            "--groups", "extra", "explicit")
    assert groups("explicit") == {"explicit", "extra"}
    sandbox("usermod", "--append", "--groups", kde_groups, "explicit")
    assert groups("explicit") == {"explicit", "extra", "wheel"} | TARGET_GROUPS
    sandbox("useradd", "--no-log-init", "--system", "--no-create-home",
            "--user-group", "--shell", "/usr/sbin/nologin", "daemon-test")
    assert groups("daemon-test") == {"daemon-test"}
    assert groups("existing") == {"existing", "wheel", "plugdev"}

    # Execute the branch's actual workbook and payload account commands after
    # configuring defaults. The Bash-shell updater is still a system account;
    # the ordinary Homebrew builder must explicitly opt out of device groups.
    payload = (ROOT / "disk_config/tools/build-tools.sh").read_text()
    accounts = set()
    for source in (build, payload):
        for line in source.replace("\\\n", "").splitlines():
            if line.startswith("useradd "):
                command = shlex.split(line)
                sandbox(*command)
                user = command[-1]
                accounts.add(user)
                assert groups(user) == {user}
                effective = sandbox("setpriv", "--reuid", user, "--regid", user,
                                    "--init-groups", "--", "id", "-nG").stdout.split()
                assert set(effective) == {user}
    assert accounts == {"ics410-workbook-update", "ics410-workbook-web", "ct-brew-build"}

    # Missing upstream config must fail before group/config changes.
    for path in (defaults, plasma):
        data = path.read_bytes()
        path.unlink()
        before_group = (etc / "group").read_bytes()
        assert sandbox("bash", "/configure-user-groups.sh", check=False).returncode != 0
        assert (etc / "group").read_bytes() == before_group
        assert not path.exists()
        path.write_bytes(data)

print("PASS isolated real useradd/usermod: normal and first-user defaults, system-account")
print("     exclusion, explicit overrides, preserved vendor/local GIDs and existing users;")
print("     KDE settings, repeat configuration, missing-config guards and build wiring")
print("     Branch workbook and Homebrew build accounts exclude device groups")
