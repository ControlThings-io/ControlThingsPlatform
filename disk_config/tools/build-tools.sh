#!/usr/bin/bash
# Prepare mutable stores in a disposable native disk-build stage. Requires the
# selected OS's manifest/helper and a nested-sandbox-capable Podman build. Only
# the populated stores and version metadata are copied to the disk-only image.
set -euo pipefail

# Aurora's /home symlink points to /var/home, which can be absent in a build
# container. Create its target before using /home for Homebrew's bottle prefix.
mkdir -p /out /var/home
mkdir -p /home/linuxbrew
# The inherited default Flatpak list is the same list Aurora's ISO uses. Optional
# CLI, fonts, DX, and other ujust Brewfiles are not disk provisioning inputs.
flatpak remote-add --system --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak config --system --set languages '*'
flatpak --default-arch > /out/flatpak-architecture.txt
# Catalog failure aborts. Only unsupported Aurora defaults on ARM64 may be omitted;
# custom apps remain required. Include runtime entries such as the Breeze theme.
flatpak remote-ls --system --app --runtime --all \
    --arch="$(cat /out/flatpak-architecture.txt)" --columns=application:full flathub \
    > /tmp/controlthings-available-flatpaks.txt
python3 /usr/libexec/controlthings-tools disk-selection \
    --available-flatpaks /tmp/controlthings-available-flatpaks.txt > /out/selection.json
python3 - <<'PY'
import json
from pathlib import Path

selection = json.loads(Path('/out/selection.json').read_text())
Path('/tmp/controlthings.Brewfile').write_text(
    ''.join(f'brew "{name}"\n' for name in selection['brew']))
Path('/tmp/controlthings-flatpaks.txt').write_text('\n'.join(selection['flatpak']) + '\n')
PY
tar --zstd -xf /usr/share/homebrew.tar.zst -C /
useradd --no-create-home --home-dir /home/linuxbrew --shell /bin/bash ct-brew-build
chown -R ct-brew-build:ct-brew-build /home/linuxbrew

# Homebrew uses its normal prefix for bottle relocation, but runs without root.
runuser -u ct-brew-build -- env HOME=/home/linuxbrew \
    HOMEBREW_NO_ANALYTICS=1 HOMEBREW_NO_AUTO_UPDATE=1 \
    /home/linuxbrew/.linuxbrew/bin/brew update
runuser -u ct-brew-build -- env HOME=/home/linuxbrew \
    HOMEBREW_NO_ANALYTICS=1 HOMEBREW_NO_AUTO_UPDATE=1 \
    /home/linuxbrew/.linuxbrew/bin/brew bundle install --no-upgrade \
    --file=/tmp/controlthings.Brewfile
runuser -u ct-brew-build -- env HOME=/home/linuxbrew HOMEBREW_NO_ANALYTICS=1 \
    /home/linuxbrew/.linuxbrew/bin/brew list --versions > /out/homebrew-versions.txt
runuser -u ct-brew-build -- env HOME=/home/linuxbrew HOMEBREW_NO_ANALYTICS=1 \
    /home/linuxbrew/.linuxbrew/bin/brew cleanup --prune=all
chown -R 1000:1000 /home/linuxbrew/.linuxbrew
rm -rf /home/linuxbrew/.cache

# Deploy now, including extra-data sandbox scripts. Nothing needs to be
# downloaded or deployed on the installed machine's first boot.
# As in Aurora's ISO builder, permit bwrap's namespace setup inside the build
# container. The caller grants SYS_ADMIN only to this manual disk-build stage.
mount -o remount,rw /proc/sys
mapfile -t apps < /tmp/controlthings-flatpaks.txt
flatpak install --system --noninteractive --assumeyes \
    --arch="$(flatpak --default-arch)" flathub "${apps[@]}"
ostree --repo=/var/lib/flatpak/repo refs | sort > /tmp/controlthings-flatpak-refs.txt
while IFS= read -r ref; do
    printf '%s %s\n' "$ref" "$(ostree --repo=/var/lib/flatpak/repo rev-parse "$ref")"
done < /tmp/controlthings-flatpak-refs.txt > /out/flatpak-commits.txt
python3 - <<'PY'
import json
from pathlib import Path

output = Path('/out')
metadata = {
    **json.loads((output / 'selection.json').read_text()),
    'architecture': (output / 'flatpak-architecture.txt').read_text().strip(),
    'homebrew_versions': (output / 'homebrew-versions.txt').read_text().splitlines(),
    'flatpak_commits': dict(line.split() for line in (output / 'flatpak-commits.txt').read_text().splitlines()),
}
(output / 'installed.json').write_text(json.dumps(metadata, indent=2) + '\n')
PY
