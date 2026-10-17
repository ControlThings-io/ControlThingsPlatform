# Decisions

## Retained disk application payload — 2026-10-16

Accepted: prepare applications once per architecture and retain the result before
assembly, so ISO, QCOW2 and assembly retries consume the same installed versions.
The user selected a separate GHCR cache package over Actions image archives.
Use `controlthingsplatform-disk-payload:run-RUNID-ATTEMPT-ARCH`; consumers use its
manifest digest, never a moving tag. This supersedes the earlier prohibition on
publishing the prepared derivative: normal OS channels still contain no app stores.
Installed systems keep their original OS update channel.

Preparation labels bind the source OS digest, update channel and preparation
recipe hash; source digest covers the shipped manifest/helper. Reuse validates
labels, platform and config identity before running the payload. Publication also
checks that the base OS layer digests remain an unchanged prefix. A separate
prepare job uploads a small descriptor before assembly jobs start. Successful
job outputs identify artifacts across re-run-failed-jobs attempts. A new dispatch
can explicitly reuse the digest with matching inputs, including after assembly
code fixes. No silent fallback to fresh application installs is allowed.

GHCR avoids a second large archive on the already constrained runner and supports
content-addressed image storage. It adds a push/pull to the first single-format
build; expected savings are for multiple formats and retries, not a promised
first-run speedup. Only preparation receives package-write permission. A source
repository label links the cache package for workflow access. Registry retention
is manual for now; automated cleanup is deferred until retention needs are known.

Keep the smoke package set while validating this transport. Full-size storage,
VM boot/upgrade and uv provisioning remain separate checks. Early dependency
manifest checks catch unavailable installer/builder pins before package work.
See [usage](../README.md#disk-builder-and-configuration) and [status](STATUS.md).


## Minimal disk validation — 2026-10-16

Accepted: temporarily comment out all custom packages except ripgrep and Okteta,
preserving the full list in place. Exclude Aurora's default Flatpak selection
during these smoke builds; keep its upstream manifest intact. First validate one
AMD64 QCOW2, then expand coverage and validate ISO before the full-size build.
The workflow defaults to QCOW2 only; smoke filenames and metadata distinguish
reduced artifacts. The manual installer also follows the reduced manifest.
No uv provisioning is implemented in this step.

Full-size storage validation remains separate: a passing smoke build cannot
establish capacity for the complete bundle. A complete Aurora fork and installer
migration remain proposals, not accepted changes. See [status](STATUS.md).


## Bundled Homebrew and Flatpak tools — 2026-10-15

Accepted, as clarified by the user: prepare the requested apps only in the manual
ISO/QCOW2 disk workflow. Normal container builds ship the shared manifest and
explicit installer, with no ControlThings app archives or automatic seeding
service. This supersedes the initial implementation that carried archives under
`/usr` in every published OS image. Sharing that cache across disk formats did
not justify its storage/update cost for existing machines.

Follow Aurora's separation: its [ISO workflow](https://github.com/get-aurora-dev/iso/blob/main/.github/workflows/reusable-build-iso-anaconda.yml)
prepares Flatpaks and its [installer hook](https://github.com/get-aurora-dev/iso/blob/main/iso_files/configure_iso_anaconda.sh)
copies the populated store into the target. Aurora's inherited
[Homebrew bootstrap](https://github.com/ublue-os/brew/blob/373e0ac907ba33269522e37fd38f45894f1bd984/Containerfile)
remains in the normal OS; it is not the requested application bundle.

Accepted follow-up: both disk formats must include Aurora's default Flatpaks
alongside ControlThings' tools. Read only `system-flatpaks.Brewfile` from the
selected OS, matching Aurora's ISO workflow, and merge/deduplicate its IDs with
`controlthings.Brewfile`. Do not scan or execute optional upstream Brewfiles.
Aurora's CLI is [opt-in](https://docs.getaurora.dev/guides/aurora-cli/), and its
developer-mode recipe separately asks about the DX Flatpak bundle. Those bundles
and fonts remain excluded, even with the Aurora DX base. Preserve all packages
already in Aurora's Homebrew bootstrap; add only the requested ControlThings
formulae. There is no default Aurora Homebrew app bundle to install separately.

Implementation choice for ARM64: Aurora's official default selection targets
AMD64, so use its available native subset on ARM64. Check a complete Flathub
app/runtime catalog before package installation, fail on lookup errors or missing
custom apps, and record/warn about omitted ARM64 defaults (currently Thunderbird).
This follows the user's earlier ZAP architecture exception without hardcoding
a permanent Thunderbird exclusion. AMD64 requires every listed default. Record
both source manifest hashes and actual selected IDs, alongside installed versions.

For both disk formats, derive a disposable local image from the verified source
digest and read its shipped manifest/helper, rather than taking the app list
from workflow HEAD. In a separate native build stage, populate the standard
Homebrew prefix as a non-root owner and fully deploy Flatpaks with dependencies
and extra-data processing. Only the resulting stores and provisioning metadata
are copied into the disk-only image's `/var`. Grant SYS_ADMIN for this manual
stage's nested Flatpak mounts, following Aurora's ISO builder. The 2026-10-16
failure investigation also established that NET_ADMIN is needed for Bubblewrap's
private loopback setup: a real isolated Podman fixture reproduces the exact CI
error without it and passes with it. Check sandbox setup before downloads,
because Flatpak may treat trigger failures as warnings. These capabilities apply
only to disk preparation. Build dependencies and temporary user accounts stay in
the disposable stage. See [validation](STATUS.md#disk-build-id-and-nested-sandbox-fixes--2026-10-16).

Disk assembly space handling (2026-10-16): after payload verification, reclaim
only this invocation's labelled, dangling tools-builder images before osbuild
creates further copies. The populated stage is not needed after final COPY.
Global Podman pruning is inappropriate for the script's local-build use; preserve
unrelated storage and final-image ancestors. Real fixture cleanup is validated;
full-size capacity still needs CI. See [current evidence](STATUS.md#disk-assembly-space-recovery--2026-10-16).

Initial installation imports image `/var`; subsequent OS upgrades preserve it,
per the [bootc filesystem contract](https://bootc.dev/bootc/bootc-filesystem.7.html#var).
Both disk formats use the locally prepared image under the original channel
name, and future updates follow that published channel. The earlier local-only
derivative and independent preparation per format are superseded by the retained
payload decision above. Record its registry digest, local image ID and actual app
versions separately from the original OS digest. Full OCI/bootc/Anaconda import validation
remains required before claiming successful offline installs.

Use `gping` for the initial `qping`, canonical `git-delta` for `delta`, one `eza`,
and include later requests `libbladerf` and `librtlsdr`. Preserve the user's RPM
removals and fish addition. Include ZAP only on AMD64, explicitly approved after
Flathub's ARM64 lookup found no ref. Set the QCOW2 root minimum to 64 GiB, also
in the local legacy config; boot partitions are additional. Legacy local disk
recipes are not migrated or augmented by this change.

One restricted Brewfile supplies disk builds and explicit
`ujust install-controlthings-tools`. Run Homebrew as its owner without upgrading
listed installed formulae, then authorize the fixed system Flatpak list via
pkexec. Existing machines receive new listed apps only through that explicit
command; container updates do not rerun provisioning. Do not modify shell
configuration merely because shell tools are installed.
The manual command remains ControlThings-only; the Aurora default merge is a
disk provisioning policy, not an expansion of the explicit command's scope.

The user approved deleting the old Gqrx preinstall declaration because that
build is unpublished and reinstalling on the development system is acceptable.
A previously tracked Gqrx may be removed once by preinstall reconciliation;
reinstall explicitly afterward.

Usage: [README.md](../README.md#bundled-homebrew-and-flatpak-tools).
Evidence and gaps: [STATUS.md](STATUS.md#bundled-homebrew-and-flatpak-tools--2026-10-15).

## CyberChef offline build — 2026-10-15

Accepted user choice: download the latest stable official CyberChef offline ZIP
at build time, install its complete contents under `/usr/share/cyberchef/`, and
provide a menu launcher and appropriate upstream icon. No webserver is needed.
Use the [GitHub release API](https://api.github.com/repos/gchq/CyberChef/releases/latest)
for asset discovery rather than scraping the live application or compiling Node
sources. Require the release asset's SHA-256 and reject unsafe ZIP paths/symlinks
or unexpected entry-point/icon layouts. Fetch the license from the same release
tag and record version, asset URL/name, and checksum alongside installed files.

Keep a stable `index.html` symlink to the versioned offline HTML. Install the
bundled 128x128 CyberChef PNG into hicolor, and use `xdg-open` from a desktop entry
in Utilities/Development. This honors the user's HTML application association,
which normally selects their browser; actual desktop launching and offline
worker operations remain integration validation, not established by extraction.

Implementation: a separate Containerfile RUN step invokes a standard-library
Python installer. `just build` supplies a fresh `CYBERCHEF_BUILD_EPOCH` argument
after the package-install step to refresh latest without forcing DNF to rerun.
Direct Podman builds need that argument refreshed explicitly. Normalize installed
file timestamps to release publication time and record no build timestamp in
metadata; identical release inputs should not cause timestamp-only payload churn.
Changes to the selected release are intentionally not reproducible across build
dates. A future pinned/classroom policy is a separate proposal, not implemented.

Usage and verification are in [README.md](../README.md#cyberchef-offline-application);
actual checks and remaining gaps are in
[STATUS.md](STATUS.md#cyberchef-offline-build--2026-10-15).

## ControlThings capture groups — 2026-10-15

Accepted user choice: mimic Aurora's group setup, using `controlthings-groups`
for both the shared script and the ujust recipe. Manage only `wireshark` and
`usbmon`; leave `dialout` to Aurora's existing `ujust dx-group` tooling. This
supersedes the discarded proposal to enforce defaults through useradd hooks.

Use an enabled systemd oneshot service and a version marker, following
[Aurora's script](https://github.com/get-aurora-dev/common/blob/f813004dd14804a674ea22f45dd538f0d4b56f08/system_files/shared/usr/libexec/aurora-groups.sh).
Automatic setup adds all current wheel members once per setup version, including
existing administrators. Iterate the full array, correcting Aurora's first-entry
expansion. Leave setup pending if no wheel users exist yet, and write the marker
only after every membership change succeeds. Failed setup may leave earlier
successful additions in place; retrying is safe.

The `ujust controlthings-groups` recipe authorizes the same root script with
`--user` for the invoking local account. This explicit path bypasses the marker
and does not update it. New accounts after automatic setup require the command;
this is no longer a creation-time guarantee for all regular users. Preserve
other group memberships with `usermod --append`. Like Aurora, copy vendor-only
group entries into `/etc/group` before changing memberships; preserve their
GIDs, and create missing groups with groupadd. Keep one membership implementation
shared by the boot service and interactive command. No new useradd hook, kernel
module loading, or device-permission policy is included.

Usage is in [README.md](../README.md#controlthings-capture-groups); validation and
remaining integration checks are in
[STATUS.md](STATUS.md#controlthings-capture-groups--2026-10-15).

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
inherited from Aurora. Prepare the disk-only stores once and retain their image
as described above; each assembly job pulls that digest and tags it locally with
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
embeds the disk-only payload with its populated `/var`. The existing local Justfile builder migration
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
