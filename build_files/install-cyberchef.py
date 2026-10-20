#!/usr/bin/env python3
"""Install the latest stable official CyberChef offline release during the build.

Run as ``python3 /ctx/install-cyberchef.py`` inside the image build. Requires only
Python's standard library and HTTPS access to GitHub. Reject absent SHA256 data,
checksum mismatches, unsafe ZIP entries, or unexpected HTML/icon layouts. Record
release identity without timestamps, preserving identical files across builds
of the same release. Temporary downloads are removed on success or failure.
"""

import hashlib
from datetime import datetime
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
from typing import Any
from urllib.request import Request
import zipfile

import github_api
import http_download


RELEASE_API = "https://api.github.com/repos/gchq/CyberChef/releases/latest"


def download(url: str, destination: Path) -> None:
    """Download an asset without credentials, retrying transient failures twice."""
    request = Request(url, headers={"User-Agent": "ControlThingsPlatform-build"})
    http_download.download(request, destination)


def select_asset(release: dict[str, Any]) -> dict[str, Any]:
    """Select exactly one offline ZIP from a stable, versioned GitHub release."""
    tag = release["tag_name"]
    if release.get("draft") or release.get("prerelease") or not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("Expected a stable CyberChef vMAJOR.MINOR.PATCH release")
    assets = [asset for asset in release["assets"]
              if asset["name"].startswith("CyberChef_") and asset["name"].endswith(".zip")]
    if len(assets) != 1:
        raise ValueError("Expected exactly one CyberChef offline ZIP asset")
    asset = assets[0]
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", asset.get("digest") or ""):
        raise ValueError("CyberChef release asset is missing a SHA256 digest")
    prefix = f"https://github.com/gchq/CyberChef/releases/download/{tag}/"
    if not asset["browser_download_url"].startswith(prefix):
        raise ValueError("Expected an official CyberChef release download URL")
    return asset


def install(release: dict[str, Any], archive: Path, license_file: Path, root: Path) -> None:
    """Verify/extract an offline archive and install it, its license, and menu icon.

    ``root`` is the image root, or a temporary staging root for verification.
    Replace only root/usr/share/cyberchef and its installed icon after validation.
    Network/download/validation failures leave existing installation files alone;
    filesystem errors during final installation abort the image build.
    """
    asset = select_asset(release)
    checksum = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    if f"sha256:{checksum.hexdigest()}" != asset["digest"]:
        raise ValueError("CyberChef ZIP checksum does not match the release digest")
    if not license_file.read_text().strip():
        raise ValueError("CyberChef license is empty")
    published = datetime.fromisoformat(release["published_at"].replace("Z", "+00:00"))
    if published.tzinfo is None:
        raise ValueError("Release publication time must include a timezone")
    timestamp = published.timestamp()

    with tempfile.TemporaryDirectory(prefix="cyberchef-extract-") as temporary:
        staging = Path(temporary)
        with zipfile.ZipFile(archive) as source:
            for entry in source.infolist():
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in entry.filename:
                    raise ValueError(f"Unsafe ZIP path: {entry.filename}")
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError(f"ZIP symlink is not supported: {entry.filename}")
            source.extractall(staging)
        html = f'CyberChef_{release["tag_name"]}.html'
        icon = staging / "images/cyberchef-128x128.png"
        if not (staging / html).is_file() or not (staging / "assets").is_dir():
            raise ValueError("CyberChef ZIP is missing its HTML entry point or assets")
        if not icon.is_file() or icon.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("CyberChef ZIP is missing its PNG application icon")
        if (staging / "index.html").exists():
            raise ValueError("Unexpected index.html in the versioned CyberChef ZIP")
        (staging / "index.html").symlink_to(html)
        shutil.copyfile(license_file, staging / "LICENSE")
        (staging / "release.json").write_text(json.dumps({
            "version": release["tag_name"], "asset": asset["name"],
            "url": asset["browser_download_url"], "sha256": checksum.hexdigest(),
        }, indent=2) + "\n")
        # Temporary directories are private; installed content must be readable
        # by every desktop user, with deterministic permissions across umasks.
        for path in staging.rglob("*"):
            if not path.is_symlink():
                path.chmod(0o755 if path.is_dir() else 0o644)
            os.utime(path, (timestamp, timestamp), follow_symlinks=False)
        os.utime(staging, (timestamp, timestamp))
        target = root / "usr/share/cyberchef"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(staging, target, symlinks=True)
        target.chmod(0o755)
        icon_target = root / "usr/share/icons/hicolor/128x128/apps/cyberchef.png"
        icon_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target / "images/cyberchef-128x128.png", icon_target)
        icon_target.chmod(0o644)
        os.utime(icon_target, (timestamp, timestamp))
    print(f'Installed CyberChef {release["tag_name"]} ({asset["digest"]})')


def main() -> None:
    """Resolve latest once, download its ZIP/license, and install under /usr/share."""
    with tempfile.TemporaryDirectory(prefix="cyberchef-download-") as temporary:
        work = Path(temporary)
        github_api.download(RELEASE_API, work / "release.json")
        release = json.loads((work / "release.json").read_text())
        asset = select_asset(release)
        download(asset["browser_download_url"], work / "cyberchef.zip")
        download(f'https://raw.githubusercontent.com/gchq/CyberChef/{release["tag_name"]}/LICENSE',
                 work / "LICENSE")
        install(release, work / "cyberchef.zip", work / "LICENSE", Path("/"))


if __name__ == "__main__":
    main()
