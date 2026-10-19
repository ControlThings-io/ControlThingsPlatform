#!/bin/bash
# Build-only installer. Requires /run/secrets/workbook_key and network access.
# Clones the remote default branch; retains credentials intentionally for students.
# Fails on missing resources or a service using an unexpected account. Never trace
# secret contents. Seed is consumed only when the installed checkout is absent.
set +x
set -euo pipefail
umask 022
account=ics410-workbook-update
home_dir=/var/lib/ics410/workbook-update
root=/var/lib/ics410/workbook
seed=/usr/share/ics410-workbook
install -d -m 0700 -o "$account" -g "$account" "$home_dir" "$home_dir/.ssh"
install -m 0600 -o "$account" -g "$account" /run/secrets/workbook_key "$home_dir/.ssh/workbook_key"
# HTTPS authenticates the published host keys; never trust an unauthenticated scan.
curl --fail --silent --show-error --retry 3 https://api.github.com/meta -o /tmp/github-meta.json
python3 - "$home_dir/.ssh/known_hosts" <<'PY'
import json
import sys
from pathlib import Path
keys = json.loads(Path('/tmp/github-meta.json').read_text())['ssh_keys']
if not keys or any('\n' in key for key in keys):
    raise SystemExit('Invalid GitHub host keys')
Path(sys.argv[1]).write_text(''.join(f'github.com {key}\n' for key in keys))
PY
cat > "$home_dir/.ssh/config" <<CONF
Host github.com
    User git
    IdentityFile $home_dir/.ssh/workbook_key
    UserKnownHostsFile $home_dir/.ssh/known_hosts
    IdentitiesOnly yes
    BatchMode yes
    StrictHostKeyChecking yes
CONF
chown -R "$account:$account" "$home_dir"
chmod 0600 "$home_dir/.ssh/config" "$home_dir/.ssh/known_hosts"
install -d -o "$account" -g "$account" /var/lib/ics410
runuser -u "$account" -- env GIT_SSH_COMMAND="ssh -F $home_dir/.ssh/config" \
    git clone ssh://git@github.com/sans-course-workbooks/ics410-l01-workbook.git "$root"
test -f "$root/index.html"
# The deployed repository is authoritative; accept its established resource layout.
resources="$root/resources"
if [[ ! -f "$resources/ewb-update.service" ]]; then
    resources="$root/docs/resources"
fi
for file in workbook-update.sh ewb-update.service ewb-update.cron; do
    test -f "$resources/$file"
done
grep -qx 'User=ics410-workbook-update' "$resources/ewb-update.service"
runuser -u "$account" -- git -C "$root" config core.sshCommand "ssh -F $home_dir/.ssh/config"
# Symlink execution uses the target mode; retain it in the disk and boot seed.
chmod 0755 "$resources/workbook-update.sh"
ln -s "$resources/workbook-update.sh" /usr/bin/workbook-update
# Correct ExecStart's redirection without modifying the repository's service.
install -d /usr/lib/systemd/system/ewb-update.service.d
cat > /usr/lib/systemd/system/ewb-update.service.d/10-platform.conf <<CONF
[Unit]
After=ics410-workbook-init.service
Requires=ics410-workbook-init.service
[Service]
ExecStart=
ExecStart=/bin/bash $resources/workbook-update.sh
StandardOutput=null
CONF
systemctl enable "$resources/ewb-update.service"
systemctl enable ics410-workbook-init.service ics410-workbook-web.service
# Ensure allow lists, if supplied by the base, permit the dedicated account.
for kind in cron at; do
    if [[ -f /etc/$kind.allow ]]; then
        grep -qx "$account" /etc/$kind.allow || echo "$account" >> /etc/$kind.allow
    fi
    if [[ -f /etc/$kind.deny ]]; then
        sed -i "/^${account}$/d" /etc/$kind.deny
    fi
done
# Keep .git private while leaving published files readable by the web account.
chmod 0700 "$root/.git"
install -d -m 0700 "$seed"
runuser -u "$account" -- git -C "$root" rev-parse HEAD > "$seed/revision"
printf '%s\n' "${resources#"$root/"}" > "$seed/resources"
tar -C /var/lib/ics410 -cf "$seed/seed.tar" workbook workbook-update
chmod 0600 "$seed/seed.tar"
# Install now for new disks, and again at first boot for existing installations.
crontab -u "$account" "$resources/ewb-update.cron"
