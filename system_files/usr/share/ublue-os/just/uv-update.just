
# ControlThings shared Python update integration
# Appended to 00-entry.just at build time: top-level definitions win over imports.
# Delegate to the untouched Aurora recipe before shared and personal Python work.
[group('System')]
update:
    #!/usr/bin/bash
    set -euo pipefail
    /usr/bin/just --justfile /usr/share/ublue-os/just/update.just update
    /usr/libexec/uv-tools user-update
