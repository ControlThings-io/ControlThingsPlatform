# Current status

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
- Next installer check: obtain the ISO, install to a blank VM disk, remove the
  ISO, and verify boot and first login. Give matrix uploads distinct artifact
  names first; the current default name plus overwrite can replace an output.
- Source tracking: allow dated image tags, resolve the selected source once to
  a digest shared by both disk jobs, and record source metadata with artifacts.
  These workflow changes are proposed follow-ups, not implemented.
- Offline classroom validation: repeat installation and first login with the
  VM network adapter disconnected, then run the required training tools.
- Classroom account provisioning, managed home content, and bundled offline
  Python/Homebrew dependencies remain proposals, not implemented features.

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

- Disk workflow path filters still include leading `./` and the runner expression
  defaults PRs to ARM while skipping ARM dependency installation.
- A disk-image build succeeded per the user's report above. Record the workflow
  run and artifact details; publishing behavior and untested artifact formats
  still need validation.
- Upstream deprecated `osbuild/bootc-image-builder-action`; migration to its
  replacement requires separate input/output and ISO-feature review.
