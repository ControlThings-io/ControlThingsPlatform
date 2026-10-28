# ICS410 L01 decisions

## Documentation ownership — 2026-10-17

Accepted: maintain `ics410_l01` alongside `main` indefinitely. Record course-specific
choices here and current course work in [STATUS.md](STATUS.md). Course build and
operation guidance belongs in [DEVELOPMENT.md](DEVELOPMENT.md). Shared user-facing
repository guides, including root README.md and DEVELOPMENT.md, are maintained
only on main and inherited by merge. Keep shared decision/status records aligned
with main; use course records for variant differences and links for shared history.
This clarifies and supersedes the earlier omission of DEVELOPMENT.md from the
shared-document ownership rule (2026-10-19).

## Course channel and shared changes — 2026-10-17

Preserve `DEFAULT_TAG="ics410_l01"` in [image-template.env](../../image-template.env),
introduced by `64dfa77`. Merge shared fixes and infrastructure from main into the
course branch while preserving intentional course differences. Installed course
systems follow their own channel under the shared
[update-channel contract](../DECISIONS.md#disk-workflow-and-update-channels--2026-10-15).

## Base image and RPM selection — 2026-10-17

Accepted in `af3091b`: use `ghcr.io/ublue-os/aurora:stable` instead of the DX image
in [Containerfile](../../Containerfile), and explicitly add `incus`, `incus-agent`,
and `lxc` in [build.sh](../../build_files/build.sh). Keep the other shared RPM
selections. This selects the desired functionality without inheriting the complete
DX package set. Brew/Flatpak selections currently match main; any future
course-specific selection decisions belong here.

## Automatic update defaults — 2026-10-17

Accepted in `a1b1733`: disable automatic updates for new course disk installations.
The early [vendor preset](../../system_files/usr/lib/systemd/system-preset/00-controlthings-updates.preset)
disables `uupd.timer`, `rpm-ostreed-automatic.timer`, and
`bootc-fetch-apply-updates.timer`; build.sh applies it after package installation.
Disable timers rather than mask services so manual updates and the
`ujust toggle-updates` enable path remain available. Existing installations may
retain local systemd enablement choices across OS updates.

The new-user MOTD default is shared behavior from main, rather than a course-only
policy; follow its [shared decision](../DECISIONS.md#new-user-terminal-motd-default--2026-10-17).

## Local workbook — 2026-10-19

Accepted: clone the default branch of
`ssh://git@github.com/sans-course-workbooks/ics410-l01-workbook.git` on every image
build and serve its root at `http://localhost/` using Python on IPv4 loopback,
port 80. Keep the checkout at `/var/lib/ics410/workbook`; use a separate read-only
web account with only CAP_NET_BIND_SERVICE.

Use `ics410-workbook-update` for Git ownership, SSH credentials, the upstream boot
service and user crontab. Keep repository update files unchanged; enable the unit
by absolute path rather than copying it. Preserve the upstream cron/at schedule
and destructive update policy. Git SSH configuration explicitly selects the
account's SSH config despite HOME=/.

The user explicitly accepts embedding `L01_PRIVATE_KEY`, a repository-scoped
read-only deploy key, in distributed images and student VMs. Transfer it to the
builder through a secret mount, never a build argument or traced shell value.
Image recipients can extract it; runtime permissions isolate the web account.

### Simplification accepted — 2026-10-19

Populate the complete writable checkout, credentials and initial crontab during
image creation only. Preserve `/var` across OS updates. Do not provision missing
state on boot or introduce seed archives. This supersedes the earlier seed and
initializer design; existing installations without the workbook need separate
provisioning. Remove the platform systemd override and use upstream's service
unchanged; service corrections belong in the workbook repository. Rename the
platform web unit to `ewb-webserver.service` to match `ewb-update.service`.

Allow every local user to invoke `workbook-update` through a root-owned platform
launcher and a passwordless sudo rule restricted to the upstream script as the
updater account. Pass arguments, stdout, stderr and exit status through. Keep
checkout/key ownership restricted rather than granting users direct write/key
access. Cron and systemd invoke the upstream script directly; concurrency belongs
in that script, with no platform lock. Service definitions and internal paths
must be corrected upstream before guest validation.

A fresh build uses a cache-busting argument. Existing credentials require
explicit rotation. Upstream service changes require daemon-reload; changes to
[Install] require re-enablement. See [development guide](DEVELOPMENT.md#ics410-l01-workbook).

## Firefox workbook homepage — 2026-10-19

Accepted: override only `Homepage.URL` to `http://localhost/` in the inherited
[Firefox policy](../../build_files/firefox-policies.json). Keep main's six pins,
section defaults, and unlocked settings. The browser regression takes its expected
homepage from the policy to support the course URL. Shared repository guides
remain unchanged; verify fresh-user startup in the built course guest.

## Build-time GitHub API authentication — 2026-10-19

Accepted: use the Actions job's temporary `github.token` to authenticate public
API lookups during container builds. Transfer it via a private runner file and
Podman secret mounts, remove the runner file on exit, and never retain the token
in the image. Local token files are optional. Share an API-only helper between
CyberChef metadata and workbook host-key discovery; reject redirects and bound
HTTP retries/backoff. This addresses the anonymous API rate-limit failure in
run `39346663938` without changing workbook SSH credentials or runtime updates.
Shared authentication and download helpers were merged from main in `39504c2`.
The workbook build step also mounts that temporary API secret and uses the same
helper; variant-only integration remains on this branch.


## Explicit Bash workbook invocation — 2026-10-20

Accepted: the user launcher invokes the upstream script with `/bin/bash` through
sudo as the updater account. Guest testing showed the script returning to mode
0644 after an update; the supplied script runs `git reset --hard` unconditionally.
This supersedes reliance on executable mode for the user launcher.

Authorize exactly the script path with no flags, either `-verbose` or
`-debuglog`, or both in either order. This narrows the previous unrestricted
script-argument policy; repeated and unknown flags are not supported. Preserve
argument forwarding, output and exit status. Keep upstream cron/service ownership;
their invocation should also use Bash if executable mode is not tracked upstream.

## Direct workbook launcher installation — 2026-10-20

Accepted: install the root-owned launcher directly at `/usr/bin/workbook-update`.
The former symlink to `/usr/libexec/ics410-workbook-update` provided no useful
separation for this single entry point. Bash invocation and sudo authorization
remain unchanged.

## Serial device group membership — 2026-10-27

Accepted by user direction: include `dialout` in ControlThings group setup for
the same users receiving `wireshark` and `usbmon`. Apply this through the existing
boot service and manual helper; increment the setup version from 1 to 2 so
existing administrator accounts receive serial access after deployment too.
Preserve existing memberships and vendor GIDs, with the existing retry/marker
contract unchanged.

This supersedes the [shared capture-group decision](../DECISIONS.md#controlthings-capture-groups--2026-10-15)
to leave `dialout` exclusively to Aurora's DX tooling on this branch. Shared
documentation remains aligned with main; propagation to main is outstanding.
See [branch operation guidance](DEVELOPMENT.md#capture-and-serial-device-groups).

### First-boot setup retry correction — 2026-10-28

Implemented in response to the user's initial-administrator test: treat an empty
`wheel` group as temporary failure (exit 75) so the existing service retries every
30 seconds during the same boot. The previous successful empty-group exit left
setup pending until a later boot; it could miss account creation after startup.
This supersedes that deferral behavior while preserving setup version 2,
administrator selection, success markers and explicit manual setup.

The startup race is established in code and covered by the isolated regression;
guest service logs were not supplied, so the cause of the reported guest failure
is not independently confirmed. The user confirmed manual setup and membership
persistence through reboots. Corrected automatic guest setup remains unvalidated.
