# Decisions

Accepted shared choices on main. Current evidence and unfinished work belong in
[STATUS.md](STATUS.md); build instructions belong in [DEVELOPMENT.md](../DEVELOPMENT.md).
Detailed investigations and superseded implementations remain in Git history.

## Documentation ownership — 2026-10-17

Keep this file for accepted shared choices and STATUS for current work, checks,
gaps, and next steps. Long-lived variants store their own records in
`docs/<branch>/DECISIONS.md` and `docs/<branch>/STATUS.md`, linking to shared
material. Keep the shared documents aligned with main to reduce merge conflicts.
README is the project overview and user guide; DEVELOPMENT holds the former
README's build/customization instructions. Repository routing is in [AGENTS.md](../AGENTS.md).

## Explicit application selection — 2026-10-17

Prepare only the custom [Brewfile](../system_files/usr/share/ublue-os/homebrew/controlthings.Brewfile),
including explicitly selected Aurora apps. Include Bazaar before first boot to
avoid its background-install/icon delay. Do not automatically install Aurora's
system, CLI, DX, or font bundles. Keep its inherited Homebrew bootstrap.
This supersedes the earlier default-Flatpak merge and temporary smoke selection.
The full custom list is enabled; ettercap remains removed and ZAP is AMD64-only.
Custom-only payloads use `profile=controlthings`; retained smoke payloads keep
their original profile and filename. Per-user uv provisioning remains deferred.

## Bundled Homebrew and Flatpak tools — 2026-10-15

Install app stores only in manual disk preparation, not normal OS containers.
The latter ship the manifest and explicit `ujust install-controlthings-tools`
helper. This replaces the earlier app archives/automatic-seeding approach,
avoiding their cost on every OS update. Existing installs receive list additions
only through the explicit helper; it installs missing apps without removing
unlisted tools or upgrading existing Brew formulae.

Read the manifest/helper from the resolved OS digest, not workflow HEAD.
Populate Brew as a non-root owner and deploy Flatpaks, including extra-data, in a
disposable native stage. Copy only stores and metadata into disk-image `/var`;
bootc imports these initially and preserves them on upgrades. Disk preparation
alone receives SYS_ADMIN and NET_ADMIN for nested Flatpak/Bubblewrap setup.
Check that sandbox before downloads because Flatpak trigger failures can be warnings.
Prune only this invocation's labelled dangling builder images to recover space;
retain payload ancestors and unrelated storage. Full-size capacity needs validation.

The helper uses the Brew owner and authorizes the fixed system Flatpak list via
pkexec. Installing a shell tool does not itself configure it. The removed Gqrx
preinstall declaration can require one explicit reinstall on older development
installs after preinstall reconciliation.

## Retained disk application payload — 2026-10-16

Prepare once per architecture and retain the result in the separate GHCR
`controlthingsplatform-disk-payload` package under `run-RUNID-ATTEMPT-ARCH`.
Assembly/retries use its digest, preserving installed versions across both formats.
This supersedes independent preparation per format and the ban on publishing a
prepared derivative; cache images are installer inputs, not OS update channels.

Bind reuse to source OS digest, channel, recipe, platform, and config identity.
Verify publication and unchanged base-layer prefixes; reject mismatches without
silently preparing again. Only preparation receives package-write access.
Registry retention is manual. GHCR avoids a second large Actions image archive;
first-run speedup is not promised. Dependency preflight is metadata-only.

## Disk workflow and update channels — 2026-10-15

Manual disk builds offer QCOW2 (default), ISO, or both on native AMD64/ARM64
runners. A matching source architecture must exist; container CI publishes AMD64
only. Use the pinned image-builder CLI and a separate pinned Fedora 44 Anaconda
installer; legacy local Justfile disk recipes remain unmigrated and unbundled.
QCOW2 retains Btrfs with a 64 GiB root minimum.

Resolve the source once. Derive filename date/hash from its version label and
record actual digests because same-day tags may be reused and revision labels
may be inherited. Embed/install the local prepared payload; installed systems
follow the originating OS channel. Preserve `ics410_l01` and `ics410-l01` as
distinct spellings. Never silently pull a different source during assembly.

Always upload separate GitHub artifacts, checksums, source metadata, and manifests.
Optional S3 paths include run/attempt/architecture/format to prevent overwrites.
See [disk instructions](../DEVELOPMENT.md#building-disk-images).

## CyberChef offline build — 2026-10-15

Download the latest stable official release ZIP at build time, verify its
published SHA-256, reject unsafe paths/symlinks, and install the complete offline
bundle with matching license/icon and release identity. Keep a stable
`/usr/share/cyberchef/index.html` link. Install Firefox as an RPM and launch
CyberChef explicitly in Firefox (2026-10-17), superseding xdg-open.

Refresh CyberChef in its own build step so freshness does not invalidate RPM
installation. Normalize file timestamps to release publication time; record no
build timestamp. Latest-release selection can change across builds; pinning for
classrooms remains a proposal. See [build details](../DEVELOPMENT.md#cyberchef-offline-application).

## Build-time GitHub API authentication — 2026-10-19

Accepted: authenticate CyberChef release metadata requests using the Actions
job's temporary `github.token`, passed via a private runner file and Podman build
secret. Delete the runner file on exit; never persist the token in image layers
or pass it as a build argument. Local token files are optional. Scope credentials
to `https://api.github.com`, reject API redirects, and bound HTTP retries/backoff.
The API helper can be reused by variant installers; main has no workbook setup.
This addresses the anonymous API rate-limit failure observed in course run
`39346663938`. Latest release selection and checksum verification remain intact.
Extend the bounded retry policy to CyberChef ZIP/license downloads and transient
network failures, including truncated transfers. Keep those requests anonymous
and retain checksum verification. Authenticate eligible jobs before image pulls;
rootful Podman receives an explicit temporary auth file, cleaned up with
`always()`. Preserve Docker authentication for signing and existing branch/PR
conditions. See [build instructions](../DEVELOPMENT.md#cyberchef-offline-application).

## ControlThings capture groups — 2026-10-15

Use one shared root script for a versioned boot oneshot and the explicit
`ujust controlthings-groups` command. Automatically add all current wheel members
to `wireshark` and `usbmon`; leave setup pending without wheel users and mark
success only after all changes succeed. Preserve existing memberships and vendor
GIDs. Manual `--user` setup bypasses the marker for later accounts.

This replaces the useradd-hook proposal. Dialout stays with Aurora's DX tooling;
module loading and device-permission policy are outside this feature. Actual
capture permissions still require hardware validation.

## New-user terminal MOTD default — 2026-10-17

Seed `.config/no-show-user-motd` through `/etc/skel` so new users start with Aurora's
MOTD disabled and can enable it with `ujust toggle-user-motd`. Keep upstream hooks,
existing user preferences, and the custom fish Macchina display. Automatic-update
defaults on main remain inherited; course policy belongs in course records.

## Default desktop wallpaper — 2026-10-14

Use `CT-De-Machina-Logica-Programmabilis` for new desktops. Replace Aurora's dark
and light Folder View creation hooks with one script because those hooks override
ordinary theme wallpaper settings. Use the wallpaper package for screen-size
selection, preserve saved desktops, and fail the build if expected hook directories
are absent. Login-screen and installer branding are separate work.

## Default lock-screen background — 2026-10-14

Use `CT-Aquila-Aurea-Machina` through Aurora's system-default KDE profile, superseding
the initial assumption that it should match the desktop. User preferences take
precedence. Keep authentication, lock timing, and the login screen unchanged.

## Chunkah rechunking — 2026-10-15

Use pinned Chunkah in CI, matching Aurora's 256-layer packing approach. Transfer
configuration from the exact input tag, prune embedded OSTree data/stale labels,
import before retagging, clean temporary files, and lint the result. Renovate
maintains the pin; the legacy rechunker remains for explicit comparisons.
This does not establish smaller downloads or eliminate RPM/DNF state churn.

## Build-time DNF counting state — 2026-10-15

Disable countme only for build package operations and remove regular per-repository
countme cookies before rechunking. Two tiny cookies were observed invalidating a
409.844 MiB layer. Preserve RPM inventory, transaction history, neighboring state,
and installed-system repository settings. Reproducible RPM/DNF state and timestamp
normalization remain proposals requiring controlled measurements.

## Weekly container builds — 2026-10-15

Schedule Saturdays at 23:00 UTC (`0 23 * * 6`) instead of daily builds to reduce
scheduled rebuild frequency. Preserve push, pull-request, and manual triggers;
GitHub scheduling may be delayed.

## ZAP X11 workaround — 2026-10-17

Apply an app-specific system-wide X11 socket override after Flatpak installation
in both disk payload preparation and the explicit installer, only when ZAP is
selected. This fixes the user-reported ZAP bug for all accounts and avoids
configuring the build account. ARM64 skips it because ZAP is excluded. Existing
installs need the command documented in [README](../README.md) or the updated
installer; OS updates preserve the mutable Flatpak store.

## Editable Firefox defaults — 2026-10-19

Accepted: main starts Firefox at `https://www.controlthings.io` and provides one
row of six pinned shortcuts in the user's requested order: ControlThings Website,
ControlThings Discord, ICS410, SANS ICS, CS2AI, and Fedora Project. Widgets, stories,
and Support Firefox/sponsored content default off. Shortcuts use `url` and `label`
objects in the default `browser.newtabpage.pinned` value.

Use an unlocked homepage policy and default-status preferences in Firefox's RPM
application distribution directory under `/usr`. Avoid prebuilt skeleton profiles
and persistent user.js files; users may change startup behavior, section toggles,
and pins, with saved personal values taking precedence. Initial defaults are
sufficient; maintaining/updating users' customized lists is not required. Existing
profiles with no override can also receive these defaults. Changing only the L01
homepage to localhost is intended later, not part of this main-branch change.

Configuration/build and verification details are in
[DEVELOPMENT](../DEVELOPMENT.md#firefox-homepage-and-shortcuts); user controls are in
[README](../README.md#firefox-defaults).
