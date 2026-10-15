"""Run ``python3 tests/check_cyberchef.py`` without network or root privileges.

Requires Python 3.9+, Bash, and desktop-file-validate. Exercises real ZIP
verification/extraction in temporary image roots, failure cases, stable file
metadata, and the desktop entry. Browser workers and KDE launching still need
an offline desktop/VM check.
"""

from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import zipfile


sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("cyberchef", "build_files/install-cyberchef.py")
chef = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chef)

with tempfile.TemporaryDirectory(prefix="ct-cyberchef-tests-") as temporary:
    work = Path(temporary)
    archive = work / "app.zip"
    license_file = work / "LICENSE"
    license_file.write_text("Apache License, Version 2.0\n")
    release = {
        "tag_name": "v11.5.0", "published_at": "2026-09-18T11:54:00Z",
        "draft": False, "prerelease": False,
        "assets": [{"name": "CyberChef_commit.zip", "browser_download_url":
                    "https://github.com/gchq/CyberChef/releases/download/v11.5.0/CyberChef_commit.zip"}],
    }

    def write_zip(entries):
        """Make a small release fixture, including its matching API digest."""
        with zipfile.ZipFile(archive, "w") as output:
            for name, contents in entries:
                output.writestr(name, contents)
        release["assets"][0]["digest"] = "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest()

    valid = [("CyberChef_v11.5.0.html", '<link rel="icon" href="images/cyberchef-128x128.png">'),
             ("images/cyberchef-128x128.png", b"\x89PNG\r\n\x1a\nfixture"),
             ("assets/main.js", "// offline bundle"),
             ("modules/Worker.js", "// offline worker")]
    write_zip(valid)
    root = work / "root"
    chef.install(release, archive, license_file, root)
    target = root / "usr/share/cyberchef"
    icon = root / "usr/share/icons/hicolor/128x128/apps/cyberchef.png"
    assert (target / "index.html").readlink() == Path("CyberChef_v11.5.0.html")
    assert (target / "index.html").read_text() == valid[0][1]
    assert (target / "modules/Worker.js").is_file()
    assert icon.read_bytes() == valid[1][1]
    assert (target / "LICENSE").read_text() == license_file.read_text()
    assert json.loads((target / "release.json").read_text())["version"] == "v11.5.0"
    timestamp = datetime.fromisoformat(release["published_at"].replace("Z", "+00:00")).timestamp()
    for path in [target, icon, *target.rglob("*")]:
        assert path.lstat().st_mtime == timestamp, path
        if not path.is_symlink():
            assert stat.S_IMODE(path.stat().st_mode) == (0o755 if path.is_dir() else 0o644)
    original = (target / "release.json").read_bytes()
    (target / "stale.html").touch()
    chef.install(release, archive, license_file, root)
    assert not (target / "stale.html").exists()
    assert (target / "release.json").read_bytes() == original
    assert target.stat().st_mtime == timestamp

    def expect_failure():
        """Validation must fail before replacing a pre-existing installation."""
        try:
            chef.install(release, archive, license_file, root)
        except (ValueError, zipfile.BadZipFile):
            pass
        else:
            raise AssertionError("Invalid release/archive accepted")
        assert (target / "release.json").read_bytes() == original

    archive.write_bytes(b"corrupt download")
    expect_failure()
    write_zip(valid)
    asset = release["assets"][0]
    digest = asset.pop("digest")
    expect_failure()
    asset["digest"] = digest
    release["prerelease"] = True
    expect_failure()
    release["prerelease"] = False
    release["assets"].append(dict(asset))
    expect_failure()
    release["assets"].pop()
    for bad_entries in ([item for item in valid if not item[0].endswith(".html")],
                        [item for item in valid if not item[0].endswith(".png")],
                        valid + [("../outside", "unsafe")],
                        valid + [("/absolute", "unsafe")]):
        write_zip(bad_entries)
        expect_failure()
    symlink = zipfile.ZipInfo("link")
    symlink.create_system = 3
    symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
    write_zip(valid + [(symlink, "/etc/passwd")])
    expect_failure()
    assert not (work / "outside").exists()

desktop = Path("system_files/usr/share/applications/cyberchef.desktop")
subprocess.run(["desktop-file-validate", str(desktop)], check=True)
assert "Exec=xdg-open file:///usr/share/cyberchef/index.html" in desktop.read_text()
assert "Icon=cyberchef\n" in desktop.read_text()
subprocess.run(["bash", "-n", "build_files/build.sh"], check=True)
containerfile = Path("Containerfile").read_text()
assert containerfile.index("ARG CYBERCHEF_BUILD_EPOCH") > containerfile.index("/ctx/build.sh")
assert "python3 /ctx/install-cyberchef.py" in containerfile
print("PASS release selection, checksums, safe extraction, required assets, symlink, icon/license/metadata,")
print("     stable modes/timestamps, clean replacement, failure preservation, desktop entry, build syntax")
