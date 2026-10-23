# Current status

Shared main status. Layer investigation on 2026-10-19 starts at `4e88610`;
earlier application/image evidence below retains its historical scope.
[Decisions](DECISIONS.md) records accepted choices; [DEVELOPMENT.md](../DEVELOPMENT.md)
has build instructions. Variant-only work belongs in `docs/<branch>/STATUS.md`
and `DECISIONS.md`, not these shared files.

## Current work

- Implemented shared uv tools on 2026-10-22 (committed as `8fdc7a5`): ctmodbus,
  ctserial, greatfet, rfcat and urh, with managed Python 3.13. The final selection
  supersedes the earlier ctmodbus/ctserial exclusions; ctui is a required dependency,
  not a standalone selection. The common manual installer and disk preparation
  use the same manifest/helper. Stores live under `/var/lib/uv-tools`, owned by
  the reserved non-login UID/GID 395; normal OS builds create only empty stores
  and integration files. Wheel administrators receive fixed install/update
  permissions; package builds run without root or supplementary groups. Bash/fish
  permit personal overrides. URH has a desktop entry; GreatFET/RfCat USB rules ship
  with the OS. See [implementation](../DEVELOPMENT.md#shared-python-tools-with-uv)
  and [decisions](DECISIONS.md#shared-python-tools--2026-10-22).
  Manual `ujust update`/`upgrade` delegates to Aurora before shared/personal uv
  updates. A top-level recipe avoids Just's imported-recipe precedence issue.
  Automatic shared updates use the existing uupd services and timer/toggle
  behavior, with no independent timer or uv-only enabled-state gate. Existing
  tools are preserved on install reruns and manifest removal; updates never add
  missing selections. Disk metadata records runtime and dependency versions.
  Passed policy/manual-installer/payload/disk-orchestration/reuse regressions,
  actual Just recipe/alias/failure-boundary execution, Bash/fish syntax, sudoers,
  udev/desktop validation and systemd unit verification. Private namespace checks
  exercised real sysusers, privilege dropping, account collisions, normal-user
  access, unsafe permissions, additive reruns and failed-install recovery.
  Real isolated AMD64 installation/update/inventory passed with uv 0.12.24,
  CPython 3.13.16, ctmodbus 0.6.0, ctserial 0.5.0, greatfet 2026.0.0, rfcat 2.0.1
  and urh 2.10.0. All five passed offline startup as a normal user; URH used Qt
  offscreen mode and the ControlThings TUIs used a dummy terminal with automatic
  exit. URH's isolated source build also passed locally. These tests did not
  modify host installations/accounts or run real hardware operations.
  Container CI [run 39917151287](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/39917151287)
  at `8fdc7a5` failed during `uv-tools setup`: the unbooted build container had no
  `/run/lock`, so opening the maintenance lock failed before account/store setup.
  Fixed on 2026-10-23 by creating the missing lock directory in the root-only
  helper path, preserving existing system permissions and rejecting unsafe parents.
  The isolated fixture now starts with an empty `/run`; it reproduced the original
  error before the fix and passed afterward, including real sysusers/privilege
  checks, existing lock inode/mode preservation and lock-directory symlink rejection.
  The uv policy/update regression and whitespace review also passed. A corrected
  full image build and remote CI rerun remain pending.
  Remaining: fresh full image/payload build, guest login/PATH/desktop behavior,
  sudo authorization, SELinux labels, automatic service execution/toggle/retry,
  multiple real users, OS-update persistence, ARM64 builds and physical device/SDR
  backend coverage. No publication or CI rerun was performed during the repair.

- README policy clarified on 2026-10-20: repository instructions now require
  explicit approval for any README edit, with suggestions only until approved.
  Its scope is marketing and user help. The unapproved wallpaper addition was
  reverted; README matches HEAD. Development guidance remains in DEVELOPMENT
  and decisions in DECISIONS. Content and whitespace review passed.

- Implemented the Plasma Login Manager default background change to Aquila Aurea
  Machina on 2026-10-20 (committed as `f5f079b`). The build updates only
  `Image` and `PreviewImage` in Aurora's `/usr/lib/plasmalogin/defaults.conf`, using
  the existing wallpaper package, with required-file/asset guards. Administrator
  overrides in `/etc/plasmalogin.conf` retain precedence. User-supplied VM output
  established Plasma Login Manager 6.7.5, Aurora's existing wallpaper defaults,
  and no local wallpaper override; it does not validate this change.
  Isolated execution of the build block with real `kwriteconfig6`/`kreadconfig6`
  passed for both keys, preservation of other greeter/wallpaper/autologin settings,
  repeated application, and failure before mutation when the defaults file or
  wallpaper assets are absent. Bash syntax and whitespace checks passed. No image
  build, remote CI or graphical guest validation was performed. Next: deploy a
  rebuilt image and verify boot/login, logout, display cropping, local override
  precedence and persistence across an image update. See
  [configuration and validation](../DEVELOPMENT.md#default-login-screen-background).

- Completed the same-commit `0ae7fc9` image investigation: exact supplied digests
  share 232/256 layers; 24 replacements total 604,756,457 compressed bytes while
  total compressed size grows only 312 bytes. All 48 changed old/new blobs were
  SHA-256 verified and their tar payloads/metadata compared. Twenty-one layers
  (468,508,962 bytes) differ only in mtimes; the other three contain RPM/DNF
  bookkeeping changes. Same base layers, 2,599 package identities, CyberChef
  archive and Chunkah grouping; RPM changes are 12 install-time/transaction-time
  header pairs and DNF logical changes are transaction timestamps only. No
  runtime/build changes were made. See [evidence and deferred follow-up](DECISIONS.md#same-commit-layer-investigation--2026-10-19).
  Deferred by user direction on 2026-10-19: keep timestamp normalization and
  database isolation on the upstream watch list. Review Aurora’s adoption,
  measured results, and regressions before revisiting a local implementation;
  tracking links and revisit criteria are in the decision entry. This is a
  project watch-list item, not a scheduled background monitor.

- VMDK `.7z` packaging and direct QCOW2 downloads implemented on 2026-10-21
  (committed as `6d187a6`), extending the direct monolithicSparse/VM bundle work
  committed as `fb67d62`. VMDK uses host 7-Zip, LZMA2 level 5, a 32 MiB dictionary,
  two threads and non-solid mode. Temporary hard-link staging avoids another
  disk copy; compression failures remove partial archives. Latest bundles contain
  VMDK/VMX/VBOX; branch bundles contain VMDK/VMX. The same `.7z` uploads directly
  to GitHub and S3, with disk/bundle checksums and JSON metadata kept separate.
  QCOW2 uploads directly to GitHub; checksums, manifest and source metadata move
  into a separate metadata ZIP. CI QCOW2 filenames include run/attempt for unique
  direct artifact names. QCOW2 S3 layout and ISO packaging are unchanged. No format
  option was added. README and VM source templates are untouched.
  Passed `tests/check_vmdk.py`, `tests/check_build_disk.py` and
  `tests/check_disk_payload_reuse.py`: real local OSBuild QEMU-stage disk assembly,
  content/write support, UUID/configuration preservation, 7z integrity/extraction,
  exact channel membership and extracted bytes, checksums, missing-tool/partial
  compression cleanup, CI/local naming, mocked build/registry failures, workflow
  upload routing/S3 filters and embedded Bash syntax. Local 7zz version: 26.04.
  These checks use small fixtures and mocked container/registry commands; they
  do not establish full-size performance or guest boot success; subsequent CI
  evidence is recorded below. Content/link and whitespace review passed.
  User-reported monolithicSparse VMware/VirtualBox tests predate
  `fb67d62`; exact artifact identities are unrecorded. Original native failures
  used streamOptimized output (course run `39360470160`, attempt 1).
  CI attempts at `6d187a6`, runs
  [39659636082](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/39659636082)
  and [39662488106](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/39662488106),
  failed before preparation/assembly: the ISO dependency preflight received
  `manifest unknown` for the Fedora installer digest pinned in
  `disk_config/installer/Containerfile`. All three formats were selected, so the
  shared preflight blocked them together; packaging/upload changes were not reached.
  Live Skopeo metadata checks on 2026-10-21 reproduced the missing digest and
  confirmed that the current Fedora 44 tag resolves for linux/amd64. This does not
  establish why the old manifest disappeared or validate a replacement ISO build.
  The QCOW2/VMDK-only run
  [39663118651](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/39663118651)
  passed resolution and payload preparation. QCOW2 assembly, direct disk upload
  and the separate three-file metadata ZIP upload succeeded. VMDK's OSBuild
  manifest finished successfully, then export failed with `No space left on device`
  while copying the staged VMDK from the OSBuild store into `/output/vmdk` using
  `cp --reflink=auto -a`. The 7z packaging/checksum and upload steps were not reached.
  Jobs use separate runners; selecting QCOW2 did not consume the VMDK runner's
  storage. Logs establish export-time space exhaustion, but do not quantify peak
  allocated storage or the extra capacity needed. Download/guest checks remain.
  Implemented the export/storage repair (committed as `9d8568d`): the VMDK runner creates
  a private store under `/output`, uses a guarded hard-link export adapter, and
  removes the store on success/failure before UUID updates and 7z packaging.
  Export logs report logical/allocated disk size and free space. Refreshed the
  ISO installer to Fedora 44 index `sha256:28f842889ffee5a2bfc1c1bd742a15c13b2f73a41a492312410a961e457e8d63`.
  Live dependency preflight passed for AMD64 and ARM64. The sparse 5 GiB export
  regression passed with local OSBuild 193 and OSBuild 194 inside the exact pinned
  builder: same inode/allocation, content survival after store cleanup, and
  rejection of symlinks, extra files, existing destinations and failed links.
  Inspected the pinned runtime's export callback contract. Mocked runner checks
  passed cleanup/setup/failure boundaries; disk orchestration, retained payload
  and real VMDK packaging regressions passed.
  Run [39682536214](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/39682536214)
  at `9d8568d` confirms full privileged VMDK assembly and hard-link export succeeded:
  30,131,027,968 logical bytes, 30,126,514,176 allocated bytes and 9,433,157,632
  output bytes free at export. It then failed before compression because packaging
  invoked `7zz`; Ubuntu's installed `7zip` 23.01+dfsg-11 package provides `7z`.
  Verified the exact Ubuntu package contents. Fixed executable discovery to accept
  `7zz` or `7z` and reject missing tools before any VMDK assembly (`1d3d9bb`).
  Regression checks cover both command names and missing-tool early failure.
  VMDK integrity/extraction/checksums, disk orchestration and retained payload
  checks passed using the actual Ubuntu 23.01 binary on a PATH without `7zz`.
  Successful VMDK run
  [39691650438](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/39691650438)
  at `1d3d9bb` reused that payload and completed full assembly, 7z packaging,
  checksums and GitHub uploads. Timing review on 2026-10-22: VMDK job 1h53m24s;
  setup 2m01s, input pulls/manifest setup about 4m17s, OSBuild build environment
  3m57s, raw image installation/configuration 31m11s (bootc install 30m22s),
  VMDK creation 2m24s, export/object-store cleanup about 40s, then 66m34s until
  7-Zip completion, checksums/metadata about 1m30s and uploads/finalization 51s.
  The 66m34s interval includes remaining runner cleanup, validation/configuration
  and compression: 7-Zip buffered its output, so exact compression-only duration
  cannot be isolated. Disk bytes: 30,117,199,872; archive bytes: 7,847,124,461.
  The separate earlier QCOW2 job in run `39663118651` took 47m46s; these are
  different runners/runs, not a controlled benchmark. Refreshed ISO build/install,
  downloaded-byte verification and guest boot remain unvalidated. Next: validate
  downloads and guest boot; consider explicit phase timing and a compression
  speed/size benchmark before changing settings. No runtime changes made during
  this timing review. See
  [build and packaging details](../DEVELOPMENT.md#disk-builder-and-configuration).
  Retry inputs from the successful payload descriptor: source tag
  `latest-20261021-6d187a6`, payload
  `ghcr.io/controlthings-io/controlthingsplatform-disk-payload@sha256:5b9f41f506571b34b2e6fc7a1fcf591eca4bfcbfb4b05b346531eb336aa1fb81`.
  Payload retention remains manual; no new publication or CI dispatch was performed.

- Removed the manual tool installer's `pkexec` wrapper (`cd57dc9`). System
  Flatpak remote/install commands now run as the Brew owner through native
  authorization, matching the user's reported password-free Aurora behavior.
  The CLI's `install-flatpaks` action also accepts normal users. ZAP's manual
  X11 override is per-user; disk payload preparation retains its all-user override.
  Installer regression checks passed for normal-user dispatch, absence of
  elevation commands, Brew ownership/failure boundaries and architecture filtering.
  The isolated disk-payload shell regression and whitespace checks also passed.
  Package commands are mocked; no guest installation was performed. Next: deploy
  the updated image and verify `ujust install-controlthings-tools` completes
  without authentication and ZAP launches for the invoking user.

- Implemented build-time GitHub API authentication on main (`0ae7fc9`). Actions
  passes its temporary token through a private file and Podman secret; CyberChef
  uses the API-only helper with redirect rejection and bounded HTTP retries.
  ZIP/license downloads share retries for transient HTTP/network failures and
  truncated transfers. Eligible jobs authenticate before pulls, using an explicit
  temporary rootful Podman auth file; Docker login still supports signing.
  Local builds optionally use `GITHUB_API_TOKEN_FILE`. No workbook changes are
  included; the course stash is preserved. The motivating course container run
  [39346663938](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/39346663938)
  failed on anonymous CyberChef metadata lookup with HTTP 403 rate limit exceeded.
  Local API, HTTP-download, registry-login, CyberChef and workflow-tag regressions
  passed, along with Just/Bash
  syntax and whitespace checks. Fixtures cover API credential scope, redirects,
  bounded retries, token-file permissions, environment removal and cleanup after
  successful/failed builds, partial-download replacement, retry exhaustion,
  filesystem failures and registry auth-file export/cleanup. Podman and network
  requests are mocked. CyberChef
  desktop validation emitted only its existing multiple-category hint. No live
  authenticated request, image build or remote CI run was performed in those local
  checks. The user reports the new authenticated builds working on 2026-10-19;
  the tested run identity is unrecorded. See
  [build instructions](../DEVELOPMENT.md#cyberchef-offline-application).

- Added `/etc/skel/Samples` pointing to `/usr/share/controlthings/samples` on
  main (committed as `e35ccbe`). Symlink target, temporary-home copy preservation and
  whitespace checks passed. Existing homes are not migrated; fresh-user guest
  validation remains pending.

- Added `nmap` to the shared Brewfile on main (committed as `0f773a5`).
  Entry uniqueness and whitespace checks passed; installation and image builds
  were not run. Fresh prepared disk payloads include it; existing systems can
  use `ujust install-controlthings-tools` with the updated image.

- Firefox editable defaults committed on main as `8c7a9f1`: ControlThings
  homepage, one row of the six named pins in requested order, and widgets,
  stories, and sponsored content off. Policy is installed beside the RPM Firefox.
  Real isolated Firefox 158.0 checks passed for active policy, effective defaults,
  pin order/labels, unlocked preferences, and saved homepage/session restore,
  widgets and edited pin across restart. Bash syntax, policy JSON and whitespace
  checks passed. Host browser profiles were untouched. Image build, ARM64 and
  graphical guest verification remain pending. Next: fresh guest `about:policies`,
  startup, Settings and New Tab checks. See
  [build/configuration](../DEVELOPMENT.md#firefox-homepage-and-shortcuts).

- ZAP X11 workaround implemented in payload preparation and the manual installer,
  guarded by selected app ID (committed as `70a7af1`). Installer and isolated
  payload-shell regressions passed (mocked package commands), including retained
  override content and ARM64 installer omission. Bash syntax and whitespace passed.
  Updated stale test expectations to the current 16-app selection.
  Guest validation of the new system-wide override remains pending.
- Main uses Aurora DX stable. The custom Brewfile is enabled (29 formulae,
  16 AMD64 Flatpaks; ZAP excluded on ARM64). Aurora defaults remain excluded;
  selected apps are explicit. Firefox is an RPM and CyberChef launches it.
  App-list expansion is committed as `6d17d8c`; Firefox/Bazaar changes as `ec2cc8a`.
- Manual preparation retains a GHCR application payload for digest-based reuse by
  ISO/QCOW2 assembly. OS updates retain the original channel and mutable app stores.
  Legacy local disk recipes do not populate these stores.
- Main's new-user MOTD marker is committed as `8952b79`. Automatic-update defaults
  remain inherited. Course-specific policy is tracked on the course branch.

## VM validation and application selection — 2026-10-17

User-reported QCOW2 smoke results: boot, offline cold boot, ripgrep/Okteta launch,
first-user update/removal through normal Aurora tooling, reboot persistence, and
persistence across an OS update all passed. CyberChef and `/etc/skel` content worked.
Earlier QCOW2 testing also confirmed new-user desktop and lock-screen defaults.
The user now reports all Flatpak and Brew installations validated and functional.
ZAP requires the X11 workaround above. The precise tested artifact identity was
not recorded; Firefox launcher and Bazaar first-login icon checks remain unrecorded.

User reports ISO build success; download/installation testing remains pending.
No ISO offline-installation success is established.

## Retained payload implementation — 2026-10-16

- [QCOW2 run 38990955138](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/38990955138)
  at `59659b7` prepared, published, retrieved, and assembled the retained smoke
  payload; artifact archive: 8,209,935,549 bytes.
- Historical reuse inputs: source `latest-20261017-59659b7`, payload
  `ghcr.io/controlthings-io/controlthingsplatform-disk-payload@sha256:066031ab6dcddf2db1980e7cf48d3d78bea2d4f2e004ec9f7d7ec5fd0c7cc4c1`.
  These contain the old smoke selection; current apps require fresh preparation.
- ISO installer pin repair is committed as `44b5d0c`; metadata-only AMD64 ISO
  preflight passed using the historical payload. The user's later ISO build report
  supersedes the earlier instruction to dispatch it; its run identity is unrecorded.
- Full-bundle builds previously exhausted runner storage. Scoped builder cleanup
  was validated, and smoke assembly succeeded; full-size capacity is still unknown.

## Validation evidence

Historical local checks during the full-bundle work passed manifest/manual-installer,
payload shell, disk orchestration, retained reuse, workflow tagging, CyberChef,
Bash syntax, and whitespace regressions. Package commands in these fixtures are
mocked and checks preceded the user's additional Flatpaks in `6d17d8c`; they do
not prove current full-list regression success, installation, or remote CI success.

Real isolated fixtures established nested Bubblewrap setup with SYS_ADMIN plus
NET_ADMIN, copied Flatpak deployments/exports/hardlinks, Brew UID/GID preservation
across OCI transport, and scoped image cleanup. They did not establish complete
Obsidian extra-data execution or full-size bootc/Anaconda import.

| Feature | Established evidence | Remaining checks |
| --- | --- | --- |
| Disk orchestration | Both formats, architectures, channels and failure boundaries in fixtures; AMD64 smoke QCOW2 CI | Full bundle capacity, ISO blank-disk/offline install, S3 uploads; ARM64 needs a published source |
| Capture groups | Real isolated groupadd/usermod, version markers, vendor GIDs, failure/retry and recipe delegation | Boot service, KDE pkexec, effective login groups and physical packet/USB capture |
| CyberChef | Extraction/security regressions; live v11.5.0 installation smoke test on 2026-10-15; user-reported VM use | RPM Firefox launcher/icon; offline Base64, worker/SHA-256 and file input on current image |
| Backgrounds | Mocked Plasma hook; real KDE system/user precedence tests; user-reported new-user defaults | Saved choices across update/reboot; light theme and extra displays |
| Rechunking/countme | Regression/cleanup fixtures; successful historical Chunkah CI | Controlled identical-input rebuild and small-change update measurements |

## New-user terminal MOTD default — 2026-10-17

Installed Aurora Bash/fish hooks suppressed MOTD with the skeleton marker and
resumed output after its removal in temporary user homes. Host preferences were
untouched. Current-image first-login and interactive ujust toggle need VM checks.

## Image update investigations — 2026-10-15

Historical metadata/file analysis explains large downloads without equivalent
installed-size growth; exact VM network traffic was not measured.

- Same-source `9cd857d` rebuilds replaced 591,308,140 compressed bytes; visible
  differences were package-manager state. Countme cookies alone invalidated a
  409.844 MiB layer, motivating the implemented cleanup.
- `895b82a` → `0a629cc` replaced 1,225,805,091 bytes despite only 74,849,244 bytes
  of image growth. Both used identical Aurora layers and Chunkah. Repacking,
  timestamps, linker/RPM/DNF state and Python caches contributed; timestamp-only
  initramfs/wallpaper replacements totaled 355,869,404 bytes.
- Retain digests rather than relying on same-day tags. Inherited revision and
  OSTree kernel annotations were inconsistent with project/image identities;
  metadata correction remains unresolved.

Full digests, CI references, layer tables, and rejected explanations are preserved
in [the pre-cleanup status at 8952b79](https://github.com/ControlThings-io/ControlThingsPlatform/blob/8952b79/docs/STATUS.md).
Timestamp normalization, component packing, and generated-state isolation remain
proposals, not accepted fixes or measured savings.

## Next steps

1. Publish a current OS container and prepare a fresh AMD64 QCOW2 payload. Measure
   runner free space, payload/artifact sizes and guest free space for the full list.
2. Verify ZAP launches with the new system-wide override on a fresh payload and
   through the updated manual installer. Check first-user ownership, Bazaar's
   first-login icon, Firefox/CyberChef,
   MOTD toggle, and capture-group setup. Verify apps survive a normal OS update.
3. Reuse the successful payload for ISO; install to a blank disk offline, remove
   the ISO, and verify first login, tools, and `bootc status` channel. Finish the
   previously downloaded ISO test independently.
4. Validate user background persistence and real capture hardware. Publish an ARM64
   source before attempting ARM64 disks; migrate legacy local disk recipes separately.
5. Validate the shared Python implementation in a fresh AMD64 guest through manual
   and disk provisioning, automatic updates/toggle, personal overrides and physical
   devices; then validate ARM64. Managed classroom accounts/home content,
   a complete Aurora fork/installer migration, and reproducibility optimizations
   remain proposals. Do not infer release readiness from smoke checks.
