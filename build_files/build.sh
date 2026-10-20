#!/bin/bash

set -ouex pipefail

# Copy the contents of system_files/ of the git repo to /
cp -avf "/ctx/system_files"/. /

### Install packages

# Packages can be installed from any enabled yum repo on the image.
# RPMfusion repos are available by default in ublue main images
# List of rpmfusion packages can be found here:
# https://mirrors.rpmfusion.org/mirrorlist?path=free/fedora/updates/43/x86_64/repoview/index.html&protocol=https&redirect=1

# this installs a package from fedora repos
PACKAGES=(
    at
    cronie
    curl
    git
    openssh-clients
    fish
    firefox
    incus
    incus-agent
    lxc
    markdownpart
    netcat
    python3
    which
    wireshark
    xdg-utils
    xdg-native-messaging-proxy
    uv
)

# Build containers should not update repository usage-counting state.
dnf5 -y --setopt='*.countme=false' install "${PACKAGES[@]}"

# Locate the RPM's application directory on both architectures. Keep user-editable
# defaults with Firefox rather than creating or rewriting per-user profiles.
firefox_distribution="$(rpm --eval '%{_libdir}')/firefox/distribution"
test -d "$firefox_distribution"
# Do not silently replace policies inherited from a future base image.
test ! -e "$firefox_distribution/policies.json"
install -m 0644 /ctx/firefox-policies.json "$firefox_distribution/policies.json"

# Aurora's Folder View setup hook overrides the theme's default wallpaper.
# Install one shared replacement for its dark and light themes, retaining their
# other settings. Fail if the base image's theme layout changes unexpectedly.
for theme in dev.getaurora.aurora.desktop dev.getaurora.auroralight.desktop; do
    theme_dir="/usr/share/plasma/look-and-feel/${theme}"
    test -d "${theme_dir}/contents/plasmoidsetupscripts"
    install -m 0644 /ctx/plasma-desktop.js \
        "${theme_dir}/contents/plasmoidsetupscripts/org.kde.plasma.folder.js"
done

# Use a COPR Example:
#
# dnf5 -y copr enable ublue-os/staging
# dnf5 -y install package
# Disable COPRs so they don't end up enabled on the final image:
# dnf5 -y copr disable ublue-os/staging

#### Example for enabling a System Unit File

systemctl enable podman.socket
systemctl enable crond.service atd.service
useradd --system --user-group --home-dir /var/lib/ics410/workbook-update \
    --no-create-home --shell /bin/bash ics410-workbook-update
useradd --system --user-group --no-create-home --shell /usr/sbin/nologin ics410-workbook-web
# Apply the image's opt-in update policy after installing packages. Presets also
# retain these defaults when systemd initializes a newly installed system.
# Disable timers, rather than mask services, so manual updates and ujust work.
systemctl preset uupd.timer rpm-ostreed-automatic.timer bootc-fetch-apply-updates.timer
chmod 0755 /usr/libexec/controlthings-groups
systemctl enable controlthings-groups.service
chmod 0755 /usr/libexec/controlthings-tools

# Remove inherited counting cookies after package operations, before rechunking.
# Tiny changes here otherwise invalidate the large unpackaged-content layer.
# Limit cleanup to regular per-repository cookies; retain other DNF state and
# installed-system repository settings. Missing state is normal on fresh images.
if [[ -d /var/lib/dnf/repos ]]; then
    find /var/lib/dnf/repos -mindepth 2 -maxdepth 2 \
        -type f -name countme -delete
fi
