#!/bin/bash
# Execute a customized VMDK manifest inside the pinned privileged builder.
# Usage: bash run-osbuild.sh /output/NAME.osbuild-manifest.json
# Mirror image-builder 87.0.0's pkg/setup.EnsureEnvironment (cad701ad3175):
# OSBuild needs dynamic loop devices and install_exec_t before its sandbox starts.
# All mounts/labels below are container-local, except the disposable cache volume.
# Recheck this setup when updating the pinned builder. Propagate every failure.
set -euo pipefail
[[ $# == 1 && -f "$1" ]]

store=/var/cache/image-builder/store
mkdir -p "$store" /run/osbuild
chcon system_u:object_r:root_t:s0 "$store"
mount -t tmpfs tmpfs /run/osbuild
cp -p /usr/bin/osbuild /run/osbuild/osbuild
chcon system_u:object_r:install_exec_t:s0 /run/osbuild/osbuild
mount -t devtmpfs devtmpfs /dev
mount --bind /run/osbuild/osbuild /usr/bin/osbuild
exec /usr/bin/osbuild --store "$store" --output-directory /output --export vmdk "$1"
