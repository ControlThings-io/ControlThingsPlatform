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

Clarified by user direction on 2026-10-20: README contains marketing and user help
only. Agents may suggest README changes but must obtain explicit approval for
the README edit before applying it; general implementation/documentation requests
do not grant that approval. Development decisions belong here and customization
details in DEVELOPMENT.

## Explicit application selection — 2026-10-17

Prepare only the custom [Brewfile](../system_files/usr/share/ublue-os/homebrew/controlthings.Brewfile),
including explicitly selected Aurora apps. Include Bazaar before first boot to
avoid its background-install/icon delay. Do not automatically install Aurora's
system, CLI, DX, or font bundles. Keep its inherited Homebrew bootstrap.
This supersedes the earlier default-Flatpak merge and temporary smoke selection.
The full custom list is enabled; ettercap remains removed and ZAP is AMD64-only.
Custom-only payloads use `profile=controlthings`; retained smoke payloads keep
their original profile and filename. Python provisioning follows the accepted
[shared-tool direction](#shared-python-tools--2026-10-22) below.

## Shared Python tools — 2026-10-22

Accepted: use shared preinstalled Python CLI tools with uv-managed Python runtimes,
and a separate Python manifest dispatched by the existing
`ujust install-controlthings-tools` command. Allow personal installations to
override shared commands. Integrate uv tool updates into the normal ujust update
flow alongside Brew and Flatpak. Automatic uv updates must honor the existing
`ujust toggle-updates` setting; deliberate manual updates remain available when
automatic updates are disabled. The user's final selection is ctmodbus, ctserial,
greatfet, rfcat and urh, superseding the earlier ctmodbus/ctserial exclusions.
ctui remains unselected as a standalone tool but is a required dependency of both
ControlThings applications; it is installed inside their isolated environments.
This supersedes the deferred per-user-only provisioning direction. Installation
adds missing tools; the update action upgrades installed tools. The application
list is in the shared [Python manifest](../system_files/usr/share/controlthings/uv-tools.json).

Accepted layout: `/var/lib/uv-tools/{python,tools,bin}` for managed runtimes,
isolated tool environments and exported commands. These are platform choices,
not uv-prescribed system directories. uv documents configurable
[`UV_PYTHON_INSTALL_DIR`, `UV_TOOL_DIR`, and `UV_TOOL_BIN_DIR`](https://docs.astral.sh/uv/reference/storage/).
Set shared-directory variables only within shared management commands; leave
ordinary user uv commands on their personal defaults. Put the user's executable
directory ahead of the shared bin directory in supported shells. Direct commands
then use personal overrides; ordinary `uv tool list`/`uvx` do not merge stores.
Accepted ownership: a dedicated locked, non-login `uv-tools` system account owns
the shared runtime/tool/bin directories and its private cache. Keep the parent,
manifest and management code root-owned; installed content is readable/executable
as appropriate by ordinary users, but writable only by the service account/root.
Reserve UID/GID 395 across build, installation and OS updates. Reject collisions
before sysusers creation; do not borrow UID 1000 or recursively change ownership.
Application execution runs as its caller, not as `uv-tools`. The accepted account
name and path replace the earlier `ct-tools` and `/var/lib/controlthings/uv`
proposals; no installed stores exist to migrate.

Accepted authorization: local administrators in `wheel` may invoke fixed shared
install/update actions without an additional password prompt. Use a narrowly
authorized root-owned helper or systemd service that runs uv as `uv-tools`, with
fixed paths, a controlled environment/configuration and no caller-selected package,
path or shell arguments. This permission does not grant an arbitrary shell as the
service account. Other users may execute shared tools and manage their own tools.
The existing Brew-owner restriction is separate. Update shared tools and the
invoking user's tools separately, without traversing other users' homes. Serialize
shared installation and both update entry points with the same lock.

Accepted scheduling direction: mimic Brew/Flatpak within the existing automatic
update cycle, without an independent uv schedule or uv-only timer-enabled check.
This supersedes the proposed explicit timer-state gate. Inspection of upstream
[update orchestration](https://github.com/ublue-os/uupd/blob/main/cmd/update.go),
[Brew](https://github.com/ublue-os/uupd/blob/main/drv/brew/brew.go) and
[Flatpak](https://github.com/ublue-os/uupd/blob/main/drv/flatpak/flatpak.go) code on
2026-10-22 found no timer-state checks. uupd uses its module-disable configuration
and optional hardware checks; these are distinct from `toggle-updates`, which
changes timer enablement in the inspected Aurora recipe. That recipe uses
`systemctl enable`/`disable` without `--now`, so stopping an active timer immediately
is not an established upstream guarantee. Preserve upstream scheduling semantics
rather than adding a separate uv interpretation. Manual updates remain available.

Implemented integration: uupd has no uv module or documented custom-script
extension, so use `ExecStartPost` on its automatic and manual services. Upstream
failure (including failed enabled hardware checks) skips Python maintenance; a
Python failure fails the service and participates in upstream retries. This avoids
running after a failed prerequisite and preserves upstream service configuration.
The manual ujust override delegates to Aurora's original recipe before invoking
Python updates, likewise stopping on an upstream failure. Append the override to
`00-entry.just`: top-level recipes take precedence over imported definitions,
whereas the existing later `60-custom.just` import cannot override Aurora's earlier
update import. Preserve the original update recipe and its upgrade alias. Automatic shared updates
run as `uv-tools`; personal tools are updated
as the invoking user on the manual path. Any future personal automatic updater must
honor the same toggle and must not run user package operations as root. See
[uupd's supported scope](https://github.com/ublue-os/uupd/blob/main/README.md#faq).

Accepted runtime policy: require managed CPython, select compatible minor versions,
and include patch updates through `uv python upgrade` as well as
`uv tool upgrade --all`. Avoid permanent exact application-version constraints
unless intentional, since uv upgrades honor them. Python minor-version migration
needs explicit compatibility validation; patch-following environments must use
uv's supported minor-version indirection. See
[uv's runtime upgrade contract](https://docs.astral.sh/uv/concepts/python-versions/#upgrading-python-versions).
Implementation selects 3.13, verified against all five selected releases. URH has
AMD64 wheels for that series; its source-build fallback needs extra isolated build
dependencies (Cython/NumPy) and a C++ compiler. This does not establish ARM64 or
physical SDR support. Keep ctui's transitive requirement in the ControlThings
environments; do not add a shared Python site-packages directory.

Accepted delivery mechanism: disk-only preparation. Normal OS images
ship uv, the manifest, helper and shell/update integration; retained disk payloads
add populated shared stores under `/var` at their final absolute paths. Disk
installation initializes those stores; OS updates preserve them. Existing systems
use the manual installer, and application updates use the update action. Extend
retained-payload provenance with Python runtime/tool identities; metadata describes
initial provisioning, not subsequent updates. Cache contents are not retained.
GreatFET/RfCat USB access rules and the URH desktop entry ship with the OS; running
applications retain the caller's privileges. See [development details](../DEVELOPMENT.md#shared-python-tools-with-uv)
and [status](STATUS.md) for evidence and remaining work.

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

The helper uses the Brew owner and installs the fixed system Flatpak list through
native Flatpak authorization (updated 2026-10-19). The previous `pkexec` wrapper
forced an unnecessary administrator prompt, bypassing Aurora’s normal policy.
Installing a shell tool does not itself configure it. The removed Gqrx
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

Manual disk builds offer independent QCOW2 (default on), ISO, and VMDK
checkboxes as of 2026-10-19, superseding the single format/both selector.
ISO/QCOW2 use native AMD64/ARM64 runners; VMDK targets AMD64 VMware Workstation
and, for latest-channel bundles, VirtualBox. A matching source architecture must
exist; container CI publishes AMD64 only. Use the pinned image-builder CLI and a separate pinned Fedora 44 Anaconda
installer; legacy local Justfile disk recipes remain unmigrated and unbundled.
QCOW2 and VMDK retain Btrfs with a 64 GiB root minimum. VMDK shares the retained
payload and provenance handling. Empty selections and ARM64 VMDK fail before
preparation. Existing CLI preflight `both` remains an ISO/QCOW2 alias. OVA
packaging is outside this change.

Accepted replacement — 2026-10-21: build monolithicSparse directly and compress
the distribution bundle. The pinned builder generates the manifest; customize only
its VMDK stage's subformat, compression flag and output filename, then execute
OSBuild's VMDK export in that same builder. Preserve the builder's container
setup for SELinux and loop devices. Reject unexpected manifest layouts and
validate final disk capacity/subformat/extents before packaging. This avoids the
second disk conversion, not OSBuild's normal raw-disk assembly or the larger
extracted sparse disk. The initial Deflate-6 ZIP64 packaging is superseded by
the 7z decision below.

This supersedes the uncommitted 2026-10-20 native-streamOptimized-to-monolithicSparse
conversion implementation. Two native builds failed guest writes in VMware;
user testing confirmed monolithicSparse works in VMware and VirtualBox. These
reports support the subformat choice, not validation of the revised workflow.

Accepted export revision — 2026-10-21: the full-size run `39663118651`
completed VMDK assembly but exhausted storage during OSBuild's export copy.
Use a disposable OSBuild store under the mounted output directory and replace
only the standard CLI's export callback with a single-file hard-link export.
Preserve CLI validation, pipeline dependency selection and build failures.
Require exactly one regular VMDK and a new export destination; fail on a
cross-filesystem link rather than copying. Remove the private store on runner
exit before host UUID changes and compression. This avoids duplicate export
allocation and releases build intermediates before packaging. The adapter uses
OSBuild's Python CLI/object-store interfaces; review against the pinned version
when updating the builder. Full-size capacity remains a CI validation item.

The Fedora 44 ISO installer pin was refreshed to an available multiarchitecture
index on 2026-10-21 after the prior digest became unavailable. AMD64/ARM64
registry metadata checks do not establish installer build or boot compatibility.
Mirroring the installer base into a controlled registry remains a proposal;
no mirror or automatic pin refresh is implemented.

Latest-channel bundles include the versioned VMDK, VMX and VBOX; branch bundles
omit VBOX. The naming/download revision below supersedes the original fixed
VMX/VBOX filenames. Dated source tags follow their originating channel. Generate
configuration copies from the supplied templates, preserving all settings except
the approved fields: VMX display name/disk basename; VBOX disk basename, matching media UUIDs
and a fresh machine UUID per build. VMX display names are `ControlThings Platform`
for latest and `UPPERCASE_BRANCH - ControlThings Platform` otherwise. Initialize
VirtualBox's `ddb.uuid.image` in reserved VMDK descriptor space if absent, before
checksumming. Do not confuse it with a filesystem UUID or VMware's disk UUID.
Repository templates require explicit approval before edits; placeholders are
unnecessary. The supplied VBOX template's fixed machine UUID stays in the source;
each generated copy replaces it.

Accepted packaging revision — 2026-10-21: VMDK distribution must use `.7z`,
a user requirement for the destination environment, with no build-time format
option. Use one prebuilt 7z/LZMA2 archive for GitHub and S3. The pinned
upload-artifact action supports `archive: false` for direct single-file uploads.
Accept both standalone `7zz` and distribution `7z` executable names; check
availability before VMDK assembly. Ubuntu 24.04's `7zip` package provides `7z`.
Keep the existing VM membership and disk format. Implementation defaults are
level 5, a 32 MiB dictionary, two threads, and non-solid mode to limit resource
costs and allow configurations to extract independently of the large disk.
These settings are not a measured optimum. Hard-link the disk into temporary
sibling staging to avoid copying it; failed packaging removes partial archives.
JSON provenance/manifest and disk/bundle SHA-256 files remain separate: a metadata
ZIP artifact on GitHub, sibling objects on S3. Keep the unpacked VMDK locally
but exclude it from VMDK S3 uploads. Bundle names include CI run/attempt to prevent
collisions. Checksums describe final bytes after media UUID initialization.

QCOW2 uploads directly to GitHub with `archive: false`; move its checksums,
provenance and manifest into a separate metadata ZIP. This removes the existing
uncompressed ZIP wrapper without adding a compression step to the disk. The
initial CI QCOW2 run/attempt suffix is superseded by the naming revision below.
S3's individual-file layout remains.
ISO packaging remains unchanged. This supersedes the earlier VMDK ZIP decision
and combined QCOW2 image/metadata artifact. See
[packaging details](../DEVELOPMENT.md#building-disk-images).

Accepted naming and download revision — 2026-10-28: VMDK, generated VMX/VBOX and
QCOW2 share the `<image>-<channel>-YYYYMMDD-HASH-<architecture>` basename, using
the source container version label for date/hash. Repository template filenames
remain fixed. This replaces fixed output VMX/VBOX names and removes the CI-only
run/attempt suffix from QCOW2; 7z bundle names retain their CI run/attempt suffix.
Latest-channel VBOX is bundled with VMDK/VMX only. Branch bundles contain VMDK/VMX;
each branch VMDK build also emits a matching standalone VBOX as a direct GitHub
download and optional S3 object, with its own checksum in the metadata download.
Initialize the media UUID before disk hashing on every channel, and generate a
fresh machine UUID for each VBOX. Users place a separate VBOX beside the extracted
VMDK. QCOW2 remains a separate direct download. The selected source channel,
including dated tags, controls this behavior independently of checkout branch.
Direct QCOW2 and branch VBOX retries replace the same-named artifact within that
workflow run. Supply the actual generated filename to the upload action's
`overwrite` path; separate workflow runs keep their own downloads.

Resolve the source once. Derive filename date/hash from its version label and
record actual digests because same-day tags may be reused and revision labels
may be inherited. Embed/install the local prepared payload; installed systems
follow the originating OS channel. Preserve `ics410_l01` and `ics410-l01` as
distinct spellings. Never silently pull a different source during assembly.

Keep each format in its own GitHub artifact(s), with checksums, source metadata, and manifests.
Optional S3 paths include run/attempt/architecture/format to prevent overwrites.
See [disk instructions](../DEVELOPMENT.md#building-disk-images).

Accepted VM template default — 2026-10-21: use two vCPUs in both supplied
configurations. VMware uses one virtual socket with two cores (`numvcpus = "2"`,
`cpuid.coresPerSocket = "2"`); VirtualBox retains its existing CPU count of two.
This is a starting point for desktop responsiveness on student laptops, not a
measured performance claim. Lower-end Windows 11 host testing remains pending.

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

This replaces the useradd-hook proposal. Module loading and device-permission
policy are outside this feature. Actual capture permissions still require hardware
validation.

Accepted serial-group port to main — 2026-10-28: include `dialout` alongside
`wireshark` and `usbmon` in the existing boot service and manual helper. Setup
version 2 reapplies membership to existing administrators while preserving
other memberships and vendor GIDs. This supersedes the earlier decision to
delegate `dialout` exclusively to Aurora's DX tooling; the shared helper now
provides capture and serial groups consistently. The manual marker-bypass and
success-marker contracts remain unchanged. See
[operation guidance](../DEVELOPMENT.md#controlthings-capture-groups).

Accepted first-boot retry port — 2026-10-28: treat empty wheel membership as
temporary failure (exit 75) without writing the success marker. The existing
service retries every 30 seconds during the same boot, allowing setup after the
initial administrator account is created. This supersedes the earlier successful
empty-group exit that deferred setup until another boot. Preserve setup version
2, administrator selection and explicit manual setup. The isolated regression
checks administrator creation between attempts; real guest startup and effective
login groups remain validation items in [STATUS.md](STATUS.md#current-work).

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

## Default login-screen background — 2026-10-20

Accepted: use `CT-Aquila-Aurea-Machina` for the Plasma Login Manager login screen.
The user confirmed Aurora's `plasma-login-manager-6.7.5-1.fc44.x86_64` uses
`/usr/lib/plasmalogin/defaults.conf` with the image wallpaper plugin; their local
`/etc/plasmalogin.conf` has no wallpaper override. SDDM theme configuration does
not apply to this deployed login manager.

Update only the distribution's `Image` and `PreviewImage` keys using KConfig's
writer, preserving other inherited settings and administrator overrides under
`/etc`. Select the existing wallpaper package instead of duplicating images.
Fail the build if the defaults file or required wallpaper assets are missing.
This supersedes the previous choice to leave login-screen branding unchanged;
desktop and lock-screen configuration retain their separate mechanisms. See
[configuration and validation](../DEVELOPMENT.md#default-login-screen-background).

## Chunkah rechunking — 2026-10-15

Use pinned Chunkah in CI, matching Aurora's 256-layer packing approach. Transfer
configuration from the exact input tag, prune embedded OSTree data/stale labels,
import before retagging, clean temporary files, and lint the result. Renovate
maintains the pin; the legacy rechunker remains for explicit comparisons.
This does not establish smaller downloads or eliminate RPM/DNF state churn.

Accepted retry port to main — 2026-10-28: invoke the pinned builder pull at most
three times, waiting five seconds between failed invocations, then run Chunkah
once with `--pull=never`. Retry the whole pull to handle registry HTTP failures
that Podman's internal retry classification can miss. Use plain `podman pull`
for the Ubuntu runner's Podman 4.9 compatibility; internal retries remain enabled.
This supersedes the first retry patch's unsupported `--retry`/`--policy` flags.
Exhausted pulls stop before repacking/import/retagging, preserving temporary-file
cleanup. CI checks real CLI parsing plus simulated recovery/failure boundaries
before image builds; this does not establish full build/publication success.
See [current validation](STATUS.md#current-work).

## Build-time DNF counting state — 2026-10-15

Disable countme only for build package operations and remove regular per-repository
countme cookies before rechunking. Two tiny cookies were observed invalidating a
409.844 MiB layer. Preserve RPM inventory, transaction history, neighboring state,
and installed-system repository settings. Reproducible RPM/DNF state and timestamp
normalization remain proposals requiring controlled measurements.

## Same-commit layer investigation — 2026-10-19

Measured evidence, not an accepted normalization implementation. The two images
labelled `latest.20261020-0ae7fc9` are distinct builds:

- Old: `sha256:4c460c7f45deba8dbcf179bfd67ae9287de56bd906aca0358d657a22e20b46a0`,
  created label `2026-10-20T01:30:23Z`,
  [run 39353575656](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/39353575656).
- New: `sha256:3b69198f1f0db6fcd22e5f2c6f1b09237e9eb726ca7b48948a581f0b8a10e5db`,
  created label `2026-10-20T01:46:06Z`,
  [run 39355159134](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/39355159134).

Both contain 256 layers; 232 compressed digests match. The 24 replacement layers
sum to **604,756,457 bytes** (604.756 MB / 576.741 MiB). Complete compressed layer
totals are 6,690,270,731 and 6,690,271,043 bytes: growth is only **312 bytes**.
This measures replacement registry blobs, not captured client network traffic or
installed-size growth. Both logs pulled the same 256 Aurora blobs and show base
image ID `23edd628d828`, identical 12-package transactions, CyberChef v11.5.0 with
archive SHA-256 `f6478925d3eaa16ec08626a85f5b85eed10d531a5e18700615fed7ecb024cccf`,
and the same pinned Chunkah. Layer component grouping is identical.

All 48 old/new replacement blobs were downloaded and their compressed SHA-256
verified. Compared every member's payload hash, path/type/link target, size,
mtime, ownership, mode, and PAX attributes. Only mtimes and five database-related
file payloads differ; no added/removed paths or package/application payload changes
were found. Of 848 distinct changed paths, 255 are directories, 2 symlinks, and
591 regular files; 586 regular files differ only by mtime, including 460 samples.

| Replacement layer group | Layers | New compressed bytes | Observed cause |
| --- | ---: | ---: | --- |
| Large sample documents/captures | 10 | 163,902,725 | Mtimes only |
| Wallpapers | 6 | 102,959,357 | Mtimes only |
| Mixed sample/application components | 4 | 185,575,314 | Mtimes only |
| Mixed RPM components | 1 | 16,071,566 | Mtimes only, including directories and Plasma hooks |
| RPM database | 1 | 53,554,539 | Install-time fields plus mtimes |
| Unclaimed content | 1 | 78,048,530 | RPM SQLite shared-memory file plus mtimes |
| DNF history | 1 | 4,644,426 | Transaction times and SQLite state |

The **21 mtime-only layers account for 468,508,962 bytes (77.47%)**. Git checkout
mtimes enter via `COPY system_files` and `cp -avf`; the same large SANS PDF has
mtime `01:28:16Z` versus `01:45:23Z`. `install` and package hooks also generate
new mtimes. Parent directory headers recur across packed layers, so normalization
must cover directories as well as leaf files. Unchanged sample/asset bytes make
entire gzip blobs different through their tar headers.

The other three layers account for 136,247,495 bytes. Both RPM databases contain
exactly the same 2,599 package identities. Comparing all changed package headers
finds exactly 12 headers differing only in `INSTALLTIME` (1008) and `INSTALLTID`
(1128). DNF's logical tables differ only in the transaction start/end timestamps;
its SQLite main/WAL/SHM bytes differ. The fifth changed payload is RPM's SHM file.
There are no countme cookies in either unclaimed layer; the earlier cleanup is
working, but does not eliminate these independent causes. The sole changed image
config label is `org.opencontainers.image.created`; config/history metadata alone
cannot explain the 24 changed filesystem diff IDs.

Deferred proposals: controlled deterministic-mtime experiments covering copied
assets, generated files, and directory headers, followed by separate database
component isolation/cleanup experiments. Preserve RPM inventory and DNF history;
do not delete databases as a size workaround. Chunkah documents
[`SOURCE_DATE_EPOCH`](https://github.com/coreos/chunkah#highlights), but exact pinned
behavior and interaction with inherited layers must be tested. A commit-wide
epoch can stabilize same-commit rebuilds yet change unchanged assets at every
new commit. Test both identical-input rebuilds and a small subsequent source edit.
The 468.509 MB is the measured timestamp-only portion of this pair, not a proven
future saving; the first normalization deployment can itself replace layers.

### Deferred: monitor Aurora before local implementation — 2026-10-19

Accepted user direction: defer timestamp normalization and related layer-size
optimizations. Keep the existing build behavior while reviewing upstream progress
when this work is revisited. This records a project watch list; no scheduled
monitoring or GitHub notification subscription has been configured.

Watch:

- [Aurora PR #3028](https://github.com/ublue-os/aurora/pull/3028), merged
  2026-10-16: filesystem timestamp normalization and non-RPM component handling.
- [Aurora reproducibility tracker #2579](https://github.com/ublue-os/aurora/issues/2579)
  and [update-size reporting #2810](https://github.com/ublue-os/aurora/issues/2810):
  measured improvements, remaining causes, and regressions.
- [Chunkah #160](https://github.com/coreos/chunkah/issues/160): independent
  timestamp clamping without changing layer planning or image creation time.

Revisit when Aurora’s relevant stable images include the changes and useful
before/after results or operational experience are available, or when the user
prioritizes this work. Upstream normalization does not automatically cover files
modified afterward by our customization steps. Any future local change still
needs identical-input and small-source-edit comparisons; database state remains
separate from filesystem timestamps. No implementation approach is accepted yet.

## Weekly container builds — 2026-10-15

Schedule Saturdays at 23:00 UTC (`0 23 * * 6`) instead of daily builds to reduce
scheduled rebuild frequency. Preserve push, pull-request, and manual triggers;
GitHub scheduling may be delayed.

## ZAP X11 workaround — 2026-10-17

Apply an app-specific X11 socket override after Flatpak installation, only when
ZAP is selected. Disk payload preparation applies it system-wide. As of
2026-10-19, the explicit installer applies it per user so it can run without
elevating the helper; this supersedes its original system-wide behavior. The disk
override covers all accounts without configuring the build account. ARM64 skips
it because ZAP is excluded. Existing
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
