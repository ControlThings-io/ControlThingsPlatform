#!/bin/bash
# Execute a customized VMDK manifest inside the pinned privileged builder.
# Usage: bash run-osbuild.sh /output/NAME.osbuild-manifest.json
# Mirror image-builder 87.0.0's pkg/setup.EnsureEnvironment (cad701ad3175):
# OSBuild needs dynamic loop devices and install_exec_t before its sandbox starts.
# The disposable store shares /output's filesystem for hard-link export.
# Remove it on success/failure before host validation and 7z compression.
# Recheck this setup when updating the pinned builder. Propagate every failure.
set -euo pipefail
[[ $# == 1 && -f "$1" ]]

store=$(mktemp -d /output/.osbuild-store-XXXXXXXX)
trap 'rm -rf -- "$store"' EXIT
mkdir -p /run/osbuild
chcon system_u:object_r:root_t:s0 "$store"
mount -t tmpfs tmpfs /run/osbuild
install -m 0755 /run-ct-export.py /run/osbuild/osbuild
chcon system_u:object_r:install_exec_t:s0 /run/osbuild/osbuild
mount -t devtmpfs devtmpfs /dev
mount --bind /run/osbuild/osbuild /usr/bin/osbuild
/usr/bin/osbuild --store "$store" --output-directory /output --export vmdk "$1"
