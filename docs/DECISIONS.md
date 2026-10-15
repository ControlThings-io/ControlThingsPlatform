# Decisions

## Disk workflow and update channels — 2026-10-15

Accepted user choices: disk generation remains manual, offers AMD64 (default)
and ARM64, and produces separate ISO installer and QCOW2 outputs. This supersedes
the initial AMD64-only request. Filenames include the source container's date/hash
tag. Installed machines follow the originating channel:
`latest` follows `latest`; each `ics410` channel follows itself. Existing published
course tags use underscores; support hyphens too without silently translating
between different registry tags.

Resolve the selected channel or dated tag once to a Linux manifest digest for
the requested architecture. Build each format on a matching native runner.
Reject unavailable architectures; disk generation does not cross-convert the
container payload. The container workflow remains AMD64-only; publishing ARM64
payloads is separate work. Installer package selection uses x86 BIOS/EFI packages
for AMD64 and ARM EFI packages for ARM64.

Derive the filename date/hash from the container's version label, since the disk
workflow HEAD/date describe a different build, and the OCI revision label may be
inherited from Aurora. Pull the exact digest in each job and tag it locally with
the channel reference. The new builder defaults to local storage; never enable
remote source resolution in these builds. QCOW2 uses that local name as its bootc
target reference. Anaconda explicitly installs the embedded local payload while
setting the channel as its target reference. Record the actual source digest
because date/hash tags can be reused by same-day container rebuilds.

Implementation choice: invoke the pinned new
[image-builder CLI](https://github.com/osbuild/image-builder) directly. The
[replacement action](https://github.com/osbuild/image-builder-action) lacks the
output naming and generic installer configuration controls needed here. Follow
upstream's [migration guide](https://github.com/osbuild/image-builder/blob/cad701ad3175da7297b20f61775fc269e58d2cfc/doc/20-advanced/20-bootc/50-migration.md)
and recommended `bootc-generic-iso` path. A separate Fedora 44 Anaconda environment
based on the [upstream example](https://osbuild.org/docs/developer-guide/projects/image-builder/advanced/bootc/isos/)
embeds the untouched OS payload. The existing local Justfile builder migration
is separate unfinished work, not part of this workflow change.

Always upload separate GitHub artifacts, including checksums, source metadata,
and manifests. Optional S3 uploads use run/attempt/architecture/format paths so rebuilding a
date/hash tag cannot replace an earlier run's files. The installer environment
and builder are digest-pinned; dependency updates remain managed by Renovate.
The new installer must pass CI, boot, installation, offline, and channel-update
checks before claiming those behaviors are validated. See
[STATUS.md](STATUS.md#disk-workflow-migration--2026-10-15) and
[README.md](../README.md#building-disk-images).

## Chunkah rechunking — 2026-10-15

Accepted user choice: align container rechunking with Aurora. CI now calls
`just rechunk` using Chunkah in place of `just ostree-rechunk`. Follow Aurora's
[recipe](https://github.com/ublue-os/aurora/blob/main/Justfile): 256-layer maximum,
compressed OCI directory output, full source configuration transfer, pruning
`/sysroot/` contents, and removing `ostree.commit`/`ostree.final-diffid` labels.
Use the exact supplied image tag for inspection and mounting. Import before
retagging, clean temporary files on failures, and lint the final bootc image.

Pin the builder to the digest found in Aurora's
[image versions](https://github.com/ublue-os/aurora/blob/main/image-versions.yml)
at this review: `sha256:8b56578258d1d10d3e1c7b0f71a4d05317c5fde331c4f483576a1b60e65f0cea`.
Renovate maintains this pin through a custom Docker dependency matcher in
`Justfile`; future updates are independent of Aurora's exact update timing.
Keep the legacy recipe for explicit comparisons; this supersedes its use in CI.

This aligns tooling and packing settings with the base project's approach, but
does not establish smaller downloads or fix RPM/DNF state reproducibility.
The first update may replace many layers. Boot/update compatibility and
repeat-build download sizes require integration validation. See
[README.md](../README.md#rechunking) and [STATUS.md](STATUS.md#chunkah-rechunking--2026-10-15).

## Weekly container builds — 2026-10-15

Accepted user choice: replace daily scheduled container builds with Saturdays
at 23:00 UTC (`0 23 * * 6`). Keep push, pull-request, and manual triggers.
This reduces scheduled rebuild frequency; GitHub scheduling delays still apply.
See [README.md](../README.md#buildyml) for usage and
[STATUS.md](STATUS.md#weekly-container-build-schedule--2026-10-15) for validation.

## Build-time DNF counting state — 2026-10-15

Accepted: disable `countme` for build-time package installation and remove
inherited per-repository counting cookies before rechunking. Analysis of two
otherwise matching builds found that two cookies totaling 38 bytes invalidated
a 409.844 MiB compressed layer. See [STATUS.md](STATUS.md#exact-image-update-analysis--2026-10-15)
for the source digests and findings.

Use a command-scoped repository override (`--setopt='*.countme=false'`), retaining
installed-system repository configuration. At the end of `build_files/build.sh`,
remove only regular `countme` files directly inside repository directories under
`/var/lib/dnf/repos`, without following symlinks. A missing directory is allowed;
cleanup errors fail the build. Preserve RPM inventory, DNF transaction history,
and other repository state. Database reproducibility remains separate work.

This targets repeated layer churn; the first cleaned image can still require a
replacement download. Repeated builds with fixed inputs must establish the
actual savings. Usage is in [README.md](../README.md#buildsh).

## Default desktop wallpaper — 2026-10-14

Accepted user choice: new users should receive
`CT-De-Machina-Logica-Programmabilis` as their desktop wallpaper.

Implementation: replace Aurora's Folder View creation hook in both its dark
and light global themes with one shared script, `build_files/plasma-desktop.js`.
The installed Aurora themes explicitly select `/usr/share/backgrounds/default.jxl`
in that hook, so setting only a theme's `[Wallpaper]` default would not reliably
override it. Keep the rest of Aurora's theme and panel configuration intact.
Use a wallpaper package directory so Plasma can select a display-appropriate
image. Do not copy a user's desktop configuration or run a wallpaper reset at
every login. Existing desktop settings remain in the user's profile; newly
created desktops (including extra monitors/activities) use the new default.

The image build deliberately fails if either expected Aurora setup directory
is absent, making upstream theme-layout changes visible during CI. This is a
desktop default, not login-screen, lock-screen, or installer branding.

See [README.md](../README.md#default-desktop-wallpaper) for configuration and
[STATUS.md](STATUS.md) for validation and remaining work.

## Default lock-screen background — 2026-10-14

Accepted user choice: the lock-screen background should use
`CT-Aquila-Aurea-Machina`. This supersedes the initial assumption that it should
match the desktop. The desktop default remains
`CT-De-Machina-Logica-Programmabilis`.

Ship `kscreenlockerrc` in Aurora's existing
`/usr/share/kde-settings/kde-profile/default/xdg` system-default directory. Host
inspection confirms that Aurora includes this directory in `XDG_CONFIG_DIRS`.
Override only its image-plugin and wallpaper/preview defaults. Do not write
individual user profiles or mark settings immutable. User configuration takes
precedence; existing users who inherit system defaults can see the change too.
Do not alter locking behavior, authentication requirements, or the login screen.

See [README.md](../README.md#default-lock-screen-background) for usage and
[STATUS.md](STATUS.md) for validation gaps.
