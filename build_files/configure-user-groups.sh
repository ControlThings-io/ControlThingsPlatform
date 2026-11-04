#!/bin/bash
# Configure new-account groups in the unbooted image. Run as root after packages
# are installed; no user accounts or existing memberships are changed. Localize
# vendor groups with their existing GIDs, creating missing groups as needed.
# Replace only the two account-creation group settings, preserving other defaults.
# Reruns are idempotent; failures stop the image build before it can be published.
set -euo pipefail

test -f /etc/default/useradd
test -f /etc/xdg/plasmasetuprc

default_groups=(wireshark usbmon dialout plugdev)
for group in "${default_groups[@]}"; do
    if ! grep -q "^${group}:" /etc/group; then
        if entry=$(getent group "$group"); then
            printf '%s\n' "$entry" >> /etc/group
        else
            groupadd --system "$group"
        fi
    fi
done

# useradd's GROUPS applies to normal accounts, not --system accounts. Keep wheel
# exclusive to the explicit first-administrator setting below.
new_user_groups=$(IFS=,; printf '%s' "${default_groups[*]}")
python3 - "$new_user_groups" <<'PY'
from pathlib import Path
import re
import sys

path = Path('/etc/default/useradd')
lines = path.read_text().splitlines()
lines = [line for line in lines if not re.match(r'\s*GROUPS\s*=', line)]
lines.append('GROUPS=' + sys.argv[1])
path.write_text('\n'.join(lines) + '\n')
PY

# Plasma Setup finishes these additions before the new user's login. Its
# explicit list also covers account creation that overrides useradd defaults.
kwriteconfig6 --file /etc/xdg/plasmasetuprc --group Accounts --key UserGroups \
    "wheel,$new_user_groups"
