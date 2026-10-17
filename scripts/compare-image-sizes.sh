#!/usr/bin/env bash
# Compare compressed layer totals for two ControlThings GHCR tags, oldest first.
# Usage: compare-image-sizes.sh OLD_TAG NEW_TAG
# Reads registry metadata only, selecting Skopeo's default host platform.
# Reports total sizes in GiB and new-minus-old in MiB; this is neither installed
# disk usage nor the download size of an update. Exits nonzero on invalid input,
# missing tools, registry errors, or missing/invalid layer sizes.
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 OLD_TAG NEW_TAG" >&2
    exit 2
fi

for tag in "$@"; do
    if [[ ! "$tag" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$ ]]; then
        echo "Invalid image tag: $tag" >&2
        exit 2
    fi
done

for tool in skopeo jq awk; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Required command not found: $tool" >&2
        exit 1
    fi
done

repo="docker://ghcr.io/controlthings-io/controlthingsplatform"

# Print the sum of registry layer sizes in bytes, failing on incomplete metadata.
image_bytes() {
    skopeo inspect --no-tags "$repo:$1" |
        jq -er '
            .LayersData |
            if type != "array" then error("Missing layer metadata")
            elif length == 0 then error("No layer metadata")
            elif all(.[]; .Size | if type == "number" then
                . >= 0 and . == floor else false end)
            then map(.Size) | add
            else error("Invalid layer sizes") end
        '
}

old_bytes=$(image_bytes "$1")
new_bytes=$(image_bytes "$2")

printf 'Repository: %s\nOld tag: %s\nNew tag: %s\n' "${repo#docker://}" "$1" "$2"
awk -v old="$old_bytes" -v new="$new_bytes" 'BEGIN {
    printf "Old:   %.2f GiB\n", old / 1073741824
    printf "New:   %.2f GiB\n", new / 1073741824
    printf "Delta: %+.2f MiB\n", (new - old) / 1048576
}'
