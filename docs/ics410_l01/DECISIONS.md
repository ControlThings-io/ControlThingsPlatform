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
by absolute path rather than copying it. A platform drop-in corrects ExecStart
redirection. Preserve the upstream cron/at schedule and destructive update policy.
Git SSH configuration explicitly selects the account's SSH config despite HOME=/.

The user explicitly accepts embedding `L01_PRIVATE_KEY`, a repository-scoped
read-only deploy key, in distributed images and student VMs. Transfer it to the
builder through a secret mount, never a build argument or traced shell value.
The root-only image seed intentionally contains credentials for initialization;
image recipients can extract them. Runtime permissions isolate the web account.

Seed missing mutable state only; preserve existing checkout and credentials on OS
updates. A fresh build uses a cache-busting argument and records the workbook
commit. Existing credentials require explicit rotation. Upstream service changes
require daemon-reload (also performed by initialization each boot); changes to
[Install] require re-enablement. See [development guide](DEVELOPMENT.md#ics410-l01-workbook).

## Firefox workbook homepage — 2026-10-19

Accepted: override only `Homepage.URL` to `http://localhost/` in the inherited
[Firefox policy](../../build_files/firefox-policies.json). Keep main's six pins,
section defaults, and unlocked settings. The browser regression takes its expected
homepage from the policy to support the course URL. Shared repository guides
remain unchanged; verify fresh-user startup in the built course guest.
