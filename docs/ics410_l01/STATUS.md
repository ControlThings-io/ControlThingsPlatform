# ICS410 L01 current status

## Current work — 2026-10-19

Workbook integration is committed as `1ced9b1`, documentation relocation as
`b56d242`, main Firefox changes merged as `35d3b55`, and the course homepage
committed as `5934cee`. Executable updater correction is uncommitted. Shared history
remains in [shared status](../STATUS.md); accepted course choices are in
[course decisions](DECISIONS.md).

- Updater target now receives mode 0755 before image seed creation; boot
  initialization also repairs its mode in existing persistent checkouts.
  `tests/check_workbook.py` passed, including actual execution through the
  symlink, archived mode and boot-time repair. Bash syntax and whitespace passed.
  Image build and guest execution remain unverified. An upstream Git update that
  restores a non-executable file mode may require permission repair again.
- Firefox now defaults to `http://localhost/` on this branch, opening the local
  workbook. All shortcuts and other Firefox defaults remain inherited from main
  and user-editable. JSON and a comparison against main confirm only Homepage.URL
  differs in the policy; whitespace checks passed. The browser regression now
  reads the expected homepage from the policy. Guest startup verification remains
  pending; no browser runtime check was repeated for this URL-only change.
- Course uses normal Aurora stable with the existing Incus/agent/LXC and netcat
  RPM selections. OS automatic-update defaults remain disabled.
- Added workbook default-branch clone, retained read-only deploy key, writable
  checkout, linked upstream boot updater, user cron plus atd, and localhost:80
  Python web service. The updater account owns the checkout; a separate web
  account cannot access its key or Git metadata.
- Missing workbook/key state is seeded from the image on boot. Existing state
  and crontab are preserved after initialization. Normal workbook updates use
  the upstream script, which discards local edits and untracked files.
- Workflow consumes `L01_PRIVATE_KEY`; local builds require
  `WORKBOOK_SSH_KEY_FILE`. See [workbook build/operation instructions](DEVELOPMENT.md#ics410-l01-workbook).

## Documentation ownership correction — 2026-10-19

Moved course workbook build/operation guidance to [DEVELOPMENT.md](DEVELOPMENT.md)
and restored root DEVELOPMENT.md byte-for-byte from local main at `8c7a9f1`.
Updated course links. Shared repository guides are maintained on main; course
additions belong under `docs/ics410_l01/`. Main was subsequently merged as
`35d3b55`.

Checks: exact shared-guide equality with main, local Markdown link/heading
validation, conflict-marker review and `git diff --check`. No runtime checks were
needed for that documentation-only correction, which is committed as `b56d242`.

## Workbook validation — 2026-10-19

Passed: `python3 tests/check_workbook.py`, `python3 tests/check_workflow_tags.py`,
`XDG_RUNTIME_DIR=/tmp just check`, Bash syntax and `git diff --check`.
Fixtures exercise real local Git clone of a default branch, tar seed extraction,
permissions, unchanged upstream service, initialization retry/preservation, and
workflow secret-file cleanup on success/failure. Account, service, crontab and
network commands are mocked; these checks do not prove guest behavior.

Systemd verification was blocked by sandbox credential/socket restrictions.
Private repository cloning and full builds were not run: this shell cannot
resolve GitHub and the Actions secret is not available locally. No remote CI,
publication, SSH authentication or VM boot success is claimed.

Guest checks remaining: validate linked unit availability at boot, account/PAM
permission for cron and at, SELinux, IPv4 localhost browser access, offline boot,
SSH pulls under cron's HOME=/, delayed execution, persistence across reboot/OS
update, and key isolation from the web service. Verify existing-install seeding
as well as fresh ISO/QCOW2 installations. New seed keys do not rotate an existing
machine's credentials; rotation needs explicit provisioning.

## Validation evidence and gaps

- Previously verified update defaults using the installed Aurora update recipe
  and real `systemctl --root` in a temporary filesystem: all three pre-enabled
  timer links were removed by the preset, and explicitly enabling `uupd.timer`
  succeeded. Bash syntax and whitespace checks passed; host settings were not
  modified. These checks preceded the update-default commit and are not proof
  of a course image build or VM behavior.
- Main's MOTD marker is included through the completed merge. Its shell-hook
  checks are documented in [shared status](../STATUS.md#new-user-terminal-motd-default--2026-10-17).
  Course VM first-login and toggle behavior remain unverified.
- Documentation extraction checks: shared-file equality with main, relative
  file/section links, four-file scope, conflict markers, and whitespace review.
  No runtime tests, remote CI, image builds, or VM tests were run for this
  documentation-only change.

## Next steps

- Build the course image using `L01_PRIVATE_KEY` and complete the workbook guest
  checks above. Confirm the deployed repository resource paths and service account.

- Build the course OS container and prepare a fresh disk payload from that source;
  verify its channel remains `ics410_l01`.
- On a fresh course installation, check automatic timers are disabled, manual
  updates work, and `ujust toggle-updates` can enable updates.
- Verify a new user's MOTD starts disabled and `ujust toggle-user-motd` can enable
  it; confirm Bazaar's first-login icon and Firefox/CyberChef launching.
- Finish ISO installation and full-bundle capacity/offline application validation.
  Earlier QCOW2 smoke results on main do not establish the current course image's
  behavior. Per-user uv provisioning remains deferred under the shared plan.
