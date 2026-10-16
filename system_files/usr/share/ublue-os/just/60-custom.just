# Add the current user to ControlThings packet capture groups.
[group('System')]
controlthings-groups:
    #!/usr/bin/bash
    set -euo pipefail
    if (( EUID == 0 )); then
        echo "Run ujust controlthings-groups as your normal login user."
        exit 1
    fi
    pkexec /usr/libexec/controlthings-groups --user "$(id -un)"
    echo "Log out completely and log back in for the new groups to take effect."

# Add the current image's bundled tools to an existing installation.
[group('Apps')]
install-controlthings-tools:
    /usr/libexec/controlthings-tools install
