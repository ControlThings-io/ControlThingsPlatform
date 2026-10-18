# ICS410 L01 decisions

## Documentation ownership — 2026-10-17

Accepted: maintain `ics410_l01` alongside `main` indefinitely. Record course-specific
choices here and current course work in [STATUS.md](STATUS.md). Keep shared
[decisions](../DECISIONS.md), [status](../STATUS.md), and the [README](../../README.md)
aligned with main; link to shared information instead of duplicating it. No separate
course README is needed. This extraction changes only the four decision/status
files; the existing course update section in README remains untouched.

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
