# Current status

Shared main status. VMDK/format selection work on 2026-10-19 starts at `cd57dc9`;
earlier application/image evidence below retains its historical scope.
[Decisions](DECISIONS.md) records accepted choices; [DEVELOPMENT.md](../DEVELOPMENT.md)
has build instructions. Variant-only work belongs in `docs/<branch>/STATUS.md`
and `DECISIONS.md`, not these shared files.

## Current work

- Added AMD64 VMDK assembly for VMware Workstation and independent QCOW2/ISO/VMDK
  workflow checkboxes (uncommitted). QCOW2 alone defaults on; empty selections
  and ARM64 VMDK fail before preparation. All selected outputs reuse the same
  application payload, with native builder output, checksums, metadata, and
  optional S3 uploads. QCOW2/VMDK share Btrfs and the 64 GiB root minimum.
  The workflow's old `format` input is replaced by boolean inputs; local CLI
  preflight retains `both` as an ISO/QCOW2 alias. VM configuration and manual
  Workstation tests are owned by the user; OVA packaging is not included.
  Disk orchestration and retained-payload regressions passed with external
  commands mocked, including all 16 format/architecture selections, VMDK native
  target/naming/checksums, reuse without preparation, and failure propagation.
  Workflow shell syntax and whitespace checks passed. Registry inspection and
  execution of the pinned builder (`9a16a7085eb7…`) succeeded; its generic image
  listing includes VMDK, but does not expose bootc targets. This does not validate
  the bootc/Btrfs configuration. No VMDK image, remote CI run, or Workstation boot
  has been validated. Next: build VMDK from a
  current source (or matching retained payload), then manually verify boot,
  apps, offline operation, and persistence across an OS update.

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
5. Keep per-user uv provisioning deferred. Managed classroom accounts/home content,
   a complete Aurora fork/installer migration, and reproducibility optimizations
   remain proposals. Do not infer release readiness from smoke checks.
