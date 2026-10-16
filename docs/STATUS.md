# Current status

## Bundled Homebrew and Flatpak tools — 2026-10-15

- Corrected the build boundary to the user's clarified design. Normal container
  builds carry only the shared manifest/manual helper and recipe; the tools stage,
  archives, changing cache argument, seed service and Homebrew ordering override
  have been removed. Aurora's inherited bootstrap remains unchanged.
- Added Aurora's default `system-flatpaks.Brewfile` to both disk formats, read
  from the selected OS and merged with ControlThings' IDs. Firefox and Bazaar
  are included; duplicate IDs install once. Optional CLI, DX Flatpak, fonts,
  and other upstream ujust bundles are excluded. Source review found no separate
  default Homebrew formula bundle: retain the bootstrap and add our 30 formulae.
- The manual disk script prepares a disposable native image from the resolved OS
  digest. Its manifest/helper supply the selected apps. A separate build stage
  installs Brew formulae without root and fully deploys Flatpaks, including
  extra-data processing, with nested-sandbox permissions. The disk-only image
  receives populated `/var/home/linuxbrew` (UID/GID 1000), `/var/lib/flatpak`, and
  provisioning metadata, without build dependencies/accounts or app archives.
- ISO and QCOW2 both consume that local image under the original channel name,
  preserving channel updates to the normal published OS. Source metadata records
  the original digest, temporary payload image ID, both manifest checksums,
  selected package IDs, omitted ARM64 defaults, Homebrew versions and Flatpak
  commits. App versions resolve during each disk job.
  Existing installs receive newly listed tools through `ujust
  install-controlthings-tools`; no automatic ControlThings boot provisioning
  remains. Old source tags without the manifest/helper cannot use this disk path.
- Shared list: 30 unique formulae, including `libbladerf`, `librtlsdr`, `gping`
  and `git-delta`; Gqrx, Obsidian, ImHex, Okteta, and AMD64-only ZAP. ARM64 omits
  ZAP with user approval. The user's RPM removals and fish addition are retained.
  The old Gqrx preinstall file is removed as approved for the unpublished build;
  its previously tracked Gqrx may need explicit reinstallation after reconciliation.
- Live catalog verification passed with the reviewed default list: 30 Brew
  formulae and 27 Flatpak entries on AMD64; 30 formulae and 25 entries on ARM64.
  ZAP is excluded by the custom manifest's architecture annotation; Thunderbird
  is currently absent from Flathub on ARM64. The builder omits unavailable Aurora
  defaults only on ARM64, records warnings/metadata, and fails on missing custom
  tools, missing AMD64 defaults, or a failed catalog lookup.
- Investigation of previously published `latest-20261015-9cd857d` and
  `latest-20261015-895b82a` found neither disk path installed Aurora's curated
  list. The user confirmed Bazaar and Gqrx did install in the background through
  preinstall after first boot; their initial absence was timing, not a broken
  preinstall service. The new disk path prepares them before installation.
- QCOW2 retains the approved 64 GiB root minimum in both workflow and legacy
  local config. Legacy local Justfile disk recipes still do not populate apps;
  use the manual workflow or disk script for bundled images.
- Checks passed: disk orchestration across both formats/architectures/channels,
  with nine external failure stages and invalid source/payload identities,
  mismatched tool architecture, missing output, checksums and metadata; manifest,
  native default/custom selection, duplicate handling, optional-bundle exclusion,
  ARM64 omissions, catalog failure, both manifest hashes, CLI JSON output,
  explicit installer ownership/authorization/failure
  boundaries and absence of normal-container payloads; workflow tagging;
  CyberChef regression; Bash/Just syntax; whitespace review.
- Packaging smoke checks passed: the real disk-build shell extracted the inherited
  bootstrap and produced populated fixture stores/version metadata in Bubblewrap,
  with package/account/mount commands mocked. A real synthetic Flatpak installation
  retained its app, runtime, extra-data and desktop export after copying to a new
  temporary installation and removing its sources/cache. Both tests ran outside
  the session sandbox for namespace/loopback access; host installs were untouched.
- A real rootless Podman build using the final disk COPY instructions and scratch
  fixtures passed: OCI layers preserved UID/GID 1000 for the Homebrew home/prefix,
  preserved Flatpak hardlinks, and included provisioning metadata without app
  archives. Used private temporary VFS storage with no network; cleanup passed.
- Earlier live catalogs verified the requested formula names, Linux bottles for
  `libbladerf`, `librtlsdr`, and `gping`, and Flathub availability on both arches
  except ZAP on ARM64. Lynis/sqlmap are script formulae without Linux bottles.
- Remaining: publish the new normal container, then full manual disk CI, actual
  formula/dependency installation, Obsidian apply_extra in Podman's nested sandbox,
  full-payload OCI/SELinux handling, and bootc import of the prepared
  `/var` stores. Install ISO and boot QCOW2 with networking disconnected, verify
  tools and channel references, then update to the normal OS and confirm stores
  remain usable. Check KDE pkexec, Brew owner/PATH, hardware capture, free disk
  space, and explicit installation of later additions. No full container/disk
  build, VM boot, real extra-data script, remote CI or hardware test is established
  by these local tests. The real Flatpak test uses a user store and no apply_extra.
- Usage: [README.md](../README.md#bundled-homebrew-and-flatpak-tools).
  Rationale: [DECISIONS.md](DECISIONS.md#bundled-homebrew-and-flatpak-tools--2026-10-15).

## CyberChef offline build — 2026-10-15

- Added `build_files/install-cyberchef.py` to resolve the latest stable official
  release, require/verify its ZIP SHA-256, reject unsafe archive paths/symlinks,
  and install all offline files to `/usr/share/cyberchef/`. Includes a stable
  `index.html` symlink, matching release LICENSE, and `release.json` identity.
- Added `cyberchef.desktop` under the system overlay, launching the local HTML
  through xdg-open, and installation of the bundled 128x128 hicolor icon. Python
  and xdg-utils are explicit package dependencies. A separate Containerfile step
  refreshes CyberChef using a per-invocation Justfile cache argument, preserving
  cache independence for package installation. File timestamps are normalized
  to release publication time to avoid timestamp-only CyberChef payload churn.
- Checks passed: `python3 tests/check_cyberchef.py` (release/asset selection,
  missing/bad checksums, extraction, HTML/icon/worker/license/metadata presence,
  unsafe paths/symlinks, modes/timestamps, clean replacement and failure
  preservation, desktop entry validation, build syntax); `python3
  tests/check_workflow_tags.py` (eight event/ref cases, plus CyberChef cache
  argument); `XDG_RUNTIME_DIR=/tmp just check`; whitespace review.
  desktop-file-validate reported only a hint that two main categories may show
  the launcher in both menus, which is intentional.
- Live smoke test passed using fresh GitHub metadata/license and the downloaded
  official `v11.5.0` release ZIP:
  `sha256:f6478925d3eaa16ec08626a85f5b85eed10d531a5e18700615fed7ecb024cccf`.
  Installed into a temporary image root and verified the stable HTML link and
  128x128 PNG icon. No release ZIP or extracted bundle was added to the repo.
- Remaining: full container build/CI, deployed KDE menu/icon/default-browser
  check, and disconnected-network tests for Base64, SHA-256/worker processing,
  and file input. No local browser worker/launch check was performed.
  Fixture repeat-install checks prove stable installed metadata, not actual OCI
  layer/download sizes after rechunking. Direct Podman cache freshness requires
  explicitly supplying the documented build argument.
- [README.md](../README.md#cyberchef-offline-application) covers usage;
  [DECISIONS.md](DECISIONS.md#cyberchef-offline-build--2026-10-15) records scope.

## ControlThings capture groups — 2026-10-15

- Added `/usr/libexec/controlthings-groups`, an Aurora-style root setup script
  for `wireshark` and `usbmon`. Automatic setup appends both groups to all current
  wheel members once per version, preserving other memberships and vendor GIDs.
  It records success in `/etc/ublue/controlthings-groups`; no wheel members leaves
  setup pending. `--user USER` handles explicit later additions without changing
  the automatic marker. Existing administrators are included on first setup.
- Added/enabled `controlthings-groups.service` after sysusers and Aurora group setup, with retry
  on failure, and `ujust controlthings-groups` in Aurora's imported `60-custom.just`.
  The recipe uses pkexec to call the shared script for the invoking user and
  instructs logout/login. `build_files/build.sh` ensures executable script mode.
  Dialout remains outside this feature. No discarded useradd-hook files remain.
- Validation passed: `python3 tests/check_controlthings_groups.py`, using real
  groupadd/usermod in Bubblewrap namespaces with temporary account files and a
  deterministic vendor-group fixture. Covers multiple wheel accounts, manual
  user setup, primary/other membership preservation, vendor GID preservation,
  marker skip/version upgrade, empty-wheel retry, failed setup without marker,
  and mocked pkexec delegation by the real ujust recipe. Bash syntax, custom Just
  formatting, `XDG_RUNTIME_DIR=/tmp just check`, systemd enablement in a temporary
  root, and whitespace review passed. The account test ran outside the session
  sandbox to permit shadow-utils audit sockets; host accounts stayed untouched.
- Remaining: build/deploy the image; check the actual boot service and marker,
  `ujust controlthings-groups` authorization through KDE, and effective memberships
  after logout/login. Verify a newly added account using the manual command and
  packet/USB capture with the intended hardware. No container build, VM boot,
  desktop authorization, hardware capture, or remote CI performed for this change.
- [README.md](../README.md#controlthings-capture-groups) covers usage;
  [DECISIONS.md](DECISIONS.md#controlthings-capture-groups--2026-10-15) records scope.

## Disk workflow migration — 2026-10-15

- Updated `.github/workflows/build-disk.yml` to manual builds with an AMD64/ARM64
  selector and separate ISO and QCOW2 matrix outputs on native runners. A resolver
  job shares one immutable source JSON with both jobs. Distinct artifact names
  include run/attempt IDs; GitHub uploads always run, with optional S3 copies under
  separate run/architecture/format paths. Removed the deprecated action and
  unused OIDC permission.
- Added `scripts/build-disk.py` for channel/dated-tag selection, architecture
  selection, date/hash naming from container labels, pinned source
  pulls, channel retagging in local storage, build orchestration, checksums, and
  source metadata. Both formats follow the original channel after installation;
  course hyphen/underscore spellings are preserved exactly.
- CI now invokes the pinned new image-builder CLI directly. The generic ISO
  uses a separate pinned Fedora 44 Anaconda environment in
  `disk_config/installer/`, adapted from upstream's example, and embeds the
  selected payload for local installation. QCOW2 retains Btrfs and a 64 GiB root
  minimum. Existing local Justfile recipes/configs still use the legacy builder.
  Added a Renovate matcher for the workflow builder pin. Installer packages
  select x86 BIOS/EFI or ARM EFI components according to the requested platform.
- Checks passed: `python3 tests/check_build_disk.py` (channel and dated tags,
  invalid tags/labels/dates/architectures, multiarchitecture selection, both
  formats, both architectures, and three channels, filenames/checksums/metadata,
  nine command failure stages, source/payload identity and tool-architecture
  mismatch, missing output, manual
  architecture selector/native runners, action pins, installer package selection
  using mocked DNF, workflow shell syntax); Python AST and Containerfile shell syntax; ISO label
  consistency; Renovate JSON parsing and dependency regex extraction;
  `XDG_RUNTIME_DIR=/tmp just check`; `git diff --check`.
- Live read-only AMD64 resolver passed against `latest`: version
  `latest.20261015-5118339`, created `2026-10-15T19:22:11Z`, payload digest
  `sha256:4c61d402916e44374fd88a782378191151b0dce800d657101321222c5b9a50de`.
  Builder metadata and Fedora installer base digest were checked against public
  registries; both pinned builder and installer-base indexes contain AMD64 and
  ARM64 images. Live ARM64 resolution of `latest` correctly rejected its AMD64
  payload. The container workflow currently publishes AMD64 only; an ARM64
  source must be published before selecting ARM64 can build disks. These reads
  do not establish build/boot success.
- Remaining validation: first CI build of both formats on each available
  architecture; install the ISO to a blank VM disk, remove ISO, verify boot/login
  and `bootc status` channel;
  boot QCOW2 and verify the same channel. Repeat ISO installation disconnected
  from the network, then test an update on `latest` and a course channel.
  New Anaconda/package/initramfs integration, remote CI, and S3 uploads have not
  been tested. No full disk build performed locally; regression commands mock
  Podman. Renovate's full validator was not run.
- Accepted choices/rationale are in
  [DECISIONS.md](DECISIONS.md#disk-workflow-and-update-channels--2026-10-15);
  manual usage and filenames are in [README.md](../README.md#building-disk-images).

## Chunkah rechunking — 2026-10-15

- Switched the container workflow to Chunkah. The recipe matches Aurora's
  256-layer packing limit and OCI-directory import approach, transfers metadata
  from the exact source tag, prunes embedded OSTree data/removes stale labels,
  cleans temporary files, and lints the retagged bootc image.
- Pinned Aurora's reviewed builder digest; verified its public Quay image
  configuration is available (amd64, `/usr/bin/chunkah` entrypoint). Added a
  Renovate custom manager for digest updates. Legacy `ostree-rechunk` remains
  available for comparisons. Usage/rationale are in
  [README.md](../README.md#rechunking) and
  [DECISIONS.md](DECISIONS.md#chunkah-rechunking--2026-10-15).
- Checks passed: `XDG_RUNTIME_DIR=/tmp just check`; workflow tag regression
  checks for eight events/refs including Chunkah shell syntax;
  `python3 tests/check_rechunk.py` (three tags, success and five failure stages,
  config transfer, exact source selection, OCI import/tag/lint, cleanup);
  workflow YAML and sole Chunkah stage; Renovate configuration parsing and
  dependency regex extraction; `git diff --check`.
- User reports all commits, including Chunkah integration, worked. The exact
  successful CI run was not recorded here. Previous local checks mocked the
  orchestration; VM update/download measurements and Renovate's full config
  validator remain unrecorded.
- Next: build the image in CI; boot a QCOW2 and test updating an existing VM;
  verify labels, package inventory, wallpaper defaults, and absence of countme
  build state. Compare replacement-layer sizes across two fixed-input builds.
  A larger first migration download is possible; RPM/DNF database churn remains.

## Weekly container build schedule — 2026-10-15

- Changed `.github/workflows/build.yml` from daily 10:05 UTC to Saturdays at
  23:00 UTC (`0 23 * * 6`). Push, pull-request, and manual triggers are retained.
- Updated [usage](../README.md#buildyml) and
  [decision](DECISIONS.md#weekly-container-builds--2026-10-15).
- Validation: YAML parsing, exact schedule and trigger checks, confirmation that
  only the schedule line changed in the workflow, and `git diff --check` passed.
- Pending: publish the change to the default branch when authorized, then
  observe a scheduled run. No remote schedule change or workflow run performed;
  GitHub may start scheduled events late.

## Build-time DNF counting cleanup — 2026-10-15

- Implemented the accepted countme fix in `build_files/build.sh`: command-scoped
  counting override for installation, followed by removal of inherited regular
  per-repository counting cookies at the end of the build script. Other DNF
  state and installed-system repository configuration are preserved.
- Rationale is in [DECISIONS.md](DECISIONS.md#build-time-dnf-counting-state--2026-10-15);
  usage is in [README.md](../README.md#buildsh).
- Validation passed: `bash -n build_files/build.sh`, `git diff --check`, execution
  of the actual cleanup block in a temporary fixture (missing directory,
  targeted deletion, retained neighboring/nested files, symlink protection,
  and repeat execution), plus mocked execution of the actual install command
  confirming literal wildcard option and unchanged package arguments.
- Remaining: build/publish a cleaned image, verify normal VM boot and package
  inventory, then compare two builds using identical pinned inputs to confirm
  the large unpackaged-content layer stays identical. No container build or
  measured post-fix update performed. A first replacement download is expected;
  RPM/DNF database churn is still separate outstanding work.

## Exact image update analysis — 2026-10-15

The user corrected the source pair; this replaces the earlier July-to-October
comparison, which did not describe the reported VM update. Inspected GHCR
manifests/configuration and streamed the four differing layers from each image
without extracting or executing archive contents. Compared file SHA-256 hashes,
archive metadata, and resolved OSTree hardlinks (linux/amd64):

- Old: `sha256:dbbbac9ce0776c5b4113d828ee5a09f2253867aaa36b01880907990b8cbff04f`,
  created `2026-10-15T03:29:37Z`; 128 layers, 6,373,436,976 compressed bytes.
- New: `sha256:5624508b4900aa4caba25d67ff0fff0e18519a3ce4114d08f627ca8fa9a07a7f`,
  created `2026-10-15T14:49:56Z`; 128 layers, 6,373,375,825 compressed bytes.
- Both identify `latest.20261015-9cd857d`, kernel `7.2.5-200.fc44.x86_64`, and
  the same RPM input hash. Package component descriptions match; only the OSTree
  commit description differs. Date-plus-source tags cannot distinguish these
  same-day rebuilds; record digests.
- Shared: 124 layer digests / 5,782,067,685 bytes. Four replacement layers total
  591,308,140 bytes (591.308 MB / 563.915 MiB). Net size shrinks by 61,151 bytes.
  Raw manifests corroborate inspected sizes. All four uncompressed identities
  change too; this is not compression-only churn.

| Layer | New compressed bytes | File-level finding |
| --- | ---: | --- |
| 0: OSTree export metadata | 12,923,584 | Changed commit/directory-tree objects; no visible file changes |
| 17: RPM component | 54,428,743 | Only `usr/share/rpm/rpmdb.sqlite` and its `-shm` file change |
| 100: 33 components | 94,203,536 | Only DNF transaction-history SQLite database, `-shm`, and `-wal` change |
| 126: unpackaged content/initramfs | 429,752,277 | Only two tiny DNF repository `countme` files change; initramfs contents are unchanged |

The seven differing visible files are package-manager state. RPM database size
is unchanged at 154,591,232 bytes; DNF history files also retain their sizes.
The two countme files together change from 24 to 38 bytes but invalidate a
409.844 MiB layer, 72.68% of replacement-layer bytes. The directory-tree and
commit objects change as a consequence of the changed file objects and rebuild.
There are no observed application/kernel payload changes in this pair.

Build-time countme prevention/cleanup is implemented above. Proposed remaining
follow-ups: investigate reproducible RPM/DNF database handling while
preserving package inventory; isolate frequently changing state from large stable
content if needed; validate with two builds of the same pinned inputs. DNF countme
semantics and configuration are in the
[DNF5 reference](https://dnf5.readthedocs.io/en/latest/dnf5.conf.5.html).
Simply increasing the layer limit or replacing the rechunker is not yet a
validated fix.

The 591.308 MB estimate explains the bulk of the reported roughly 600 MB update;
exact network traffic above that amount remains unmeasured without VM update
logs. The analysis itself made no pipeline/runtime changes. Raw manifests,
configurations, temporary inspection scripts, and file hash inventories are in
`/tmp/ct-image-analysis` for this session only; no downloaded archives were kept.

## Container size comparison — 2026-10-15

- Added executable `scripts/compare-image-sizes.sh OLD_TAG NEW_TAG` to query
  ControlThings GHCR layer metadata and report compressed totals and size growth.
  Usage and limitations are in [README.md](../README.md#building-disk-images).
- Validation: Bash syntax and `git diff --check` passed. With mocked Skopeo
  responses and real jq/awk, checked growth, shrinkage, equal sizes, invalid
  arguments, incomplete metadata, and registry failure propagation.
- No live GHCR comparison performed; next step is running against two published
  tags with Skopeo available. ShellCheck is unavailable locally.

## Disk-image testing — 2026-10-15

The user confirmed that the downloaded QCOW2 image works and that new users
receive the expected desktop and lock-screen backgrounds. The workflow run,
source container digest, dated tag, and architecture have not yet been recorded.
This report does not establish ISO or offline-installation success.

- Pending: change both backgrounds and verify persistence through lock/unlock,
  logout/login, and reboot; verify an existing user's choices survive an update.
- Next installer check: build the migrated ISO, install to a blank VM disk,
  remove the ISO, and verify boot and first login. Distinct matrix artifact
  names, dated source tags, shared digest selection, and source metadata are now
  implemented in the [disk migration](#disk-workflow-migration--2026-10-15).
- Offline classroom validation: repeat installation and first login with the
  VM network adapter disconnected, then run the required training tools.
- Classroom account provisioning, managed home content, and bundled offline
  Python dependencies remain proposals. Homebrew/Flatpak bundling is implemented
  above, pending full image and VM validation.

## Default lock-screen background — 2026-10-14

Committed on `main` in `9cd857d`.

- Added a system-default `kscreenlockerrc` through the `system_files/` overlay,
  selecting `CT-Aquila-Aurea-Machina` per the user's corrected choice. The
  desktop remains `CT-De-Machina-Logica-Programmabilis`. The existing build
  script installs it; no new login/autostart script is needed.
- Individual user settings remain higher priority. Existing users who inherit
  system defaults can see the new background. Lock timing, authentication, and
  the pre-login screen are unchanged.
- Updated usage and rationale in [README.md](../README.md#default-lock-screen-background)
  and [DECISIONS.md](DECISIONS.md#default-lock-screen-background--2026-10-14).
- Validation passed using real `kreadconfig6`/`kwriteconfig6` against temporary
  system/user directories: fresh configuration reads the image plugin, image,
  and preview defaults; a saved user image takes precedence without modifying
  system defaults. Verified the bundled asset path and absence of lock-timing
  or password-policy settings. `git diff --check` passed.
- User confirmed the default lock-screen background works for new users in the
  QCOW2 image on 2026-10-15. Remaining: verify persistence of a user's chosen
  replacement through lock/unlock, logout/login, and reboot.

## Default desktop wallpaper — 2026-10-14

Committed on `main` in `560984f`. The user selected
`CT-De-Machina-Logica-Programmabilis` as the default wallpaper for new users.

### Implemented

- `build_files/plasma-desktop.js` selects the existing wallpaper package when
  Plasma creates a Folder View desktop. It uses the package directory so Plasma
  can choose an image suited to the screen size.
- `build_files/build.sh` installs that single script into Aurora's dark and light
  theme setup directories after package installation. Missing directories fail
  the build rather than silently dropping the customization.
- Aurora's other theme and panel settings remain inherited. Saved desktops are
  not rewritten by a login script. New desktops on additional monitors or
  activities also receive the default while an Aurora global theme is active.
- Usage and fresh-user verification are in
  [README.md](../README.md#default-desktop-wallpaper); rationale is in
  [DECISIONS.md](DECISIONS.md#default-desktop-wallpaper--2026-10-14).

### Validation

- `bash -n build_files/build.sh` and `node --check build_files/plasma-desktop.js`
  passed.
- Executed the real JavaScript using a mocked Plasma applet API. Verified the
  image plugin, configuration group/key, reload, installed package ID, and PNG
  signatures for all three image variants.
- Executed the build installation loop against temporary theme directories:
  both received the identical script with mode 0644. Removing one expected
  directory caused the loop to fail as intended.
- `git diff --check` passed.
- Inspected the host's Aurora theme setup hooks and KDE's `ShellCorona` source:
  the hook is invoked on containment creation. The host files are evidence for
  the implementation, not proof of the exact contents of a future stable image.
- User confirmed the QCOW2 image works and new users receive the expected
  desktop wallpaper on 2026-10-15; source digest remains unrecorded.

### Next steps

1. Change the desktop wallpaper, log out/in, and reboot to verify persistence.
2. Verify a pre-existing user's selected wallpaper is preserved, plus the default
   on newly created desktops and Aurora's light-theme variant.
3. Push only when requested. Login-screen and installer branding are separate
   future work; no changes to those surfaces are included here.

## Dependency workflow follow-up

The combined dependency updates and PR image-tag fix are now on `main` in
`ecc50dc` (PR #3). The user confirmed on 2026-10-14 that the combined PR #3
workflow passed. The previously recorded CI run
[38663972331](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/38663972331)
passed build, rechunking, and tagging at PR head `5b4bff6`. Registry login,
publishing, and signing were skipped on the PR event. The old PR tag regression
originated in project commit `334bf00`, which used `GITHUB_REF_NAME` for every
non-main event, including slash-containing PR merge refs.

Superseded PRs #8 and #9 are closed, as confirmed by the user on 2026-10-14.

Outstanding work:

- The disk workflow migration above replaces the old PR path filters, ARM
  runner behavior, shared upload names, and deprecated builder action. The
  newly migrated disk workflow still needs its first CI and VM validation.
- The earlier disk-image build succeeded per the user's report above; its exact
  run/artifact details remain unrecorded and do not validate the migrated ISO.
