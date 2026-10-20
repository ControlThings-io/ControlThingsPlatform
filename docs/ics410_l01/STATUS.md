# ICS410 L01 current status

## Current work — 2026-10-19

Workbook simplification is uncommitted on top of `3dd51ee`. Shared history remains
in [shared status](../STATUS.md); accepted course choices are in
[course decisions](DECISIONS.md).

- Workbook and retained deploy-key credentials are populated only during image
  creation. Removed seed archive creation, boot initialization and its unit.
  Existing `/var` state persists; missing checkouts are not provisioned on OS update.
- Removed the platform `ewb-update.service` override. The upstream service remains
  linked and unchanged. Upstream must correct its ExecStart redirection and paths;
  required settings are in [course development](DEVELOPMENT.md#changes-required-in-the-workbook-repository).
  Private upstream files were unavailable for this review; corrections are pending.
- `/usr/bin/workbook-update` now links to a root-owned launcher using passwordless,
  noninteractive sudo for only the upstream script as `ics410-workbook-update`.
  Arguments, stdout, stderr and exit status pass through. The complete `.git`
  directory remains in the checkout; credentials and metadata retain restricted
  ownership. Cron/systemd run the upstream script directly. Concurrency belongs
  upstream, with no platform lock.
- Renamed the platform web unit to `ewb-webserver.service`. It still serves
  `/var/lib/ics410/workbook` at IPv4 localhost port 80 as a separate web account.
- The updater's executable correction was committed as `8f3b701`; build-time chmod
  remains. Commit its executable bit upstream too so Git updates retain it.
- Firefox homepage remains `http://localhost/` (`5934cee`), with inherited editable
  shortcuts/defaults. Course remains on normal Aurora stable with existing RPM
  selections and OS automatic-update defaults disabled.
- Workflow still consumes `L01_PRIVATE_KEY`; local builds require
  `WORKBOOK_SSH_KEY_FILE`. See [build/operation instructions](DEVELOPMENT.md#ics410-l01-workbook).

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

Current local checks passed for the uncommitted simplification:
`python3 tests/check_workbook.py`, `python3 tests/check_workflow_tags.py`,
`XDG_RUNTIME_DIR=/tmp just check`, Bash syntax and `git diff --check`.

Workbook fixtures exercise real default-branch Git clones for both resource
layouts, retained `.git` and credential permissions, unchanged upstream unit,
initial crontab installation, renamed web-unit enablement, real visudo syntax
validation, and launcher argument/stdout/stderr/exit-status forwarding. Workflow
secret-file cleanup passes for successful and failed builds. Account ownership
commands, sudo execution, systemd, crontab and network access are mocked: these
checks do not prove actual unprivileged sudo authorization or guest behavior.

No image build, private-repository fetch, remote CI, publication, real SSH update,
or VM boot was performed for this change. Earlier systemd verification was
blocked by sandbox credential/socket restrictions; no new systemd runtime result
is claimed.

Guest checks remaining: fresh QCOW2/ISO `/var` population including `.git`, linked
unit boot availability, web serving, any unprivileged user's passwordless update
with visible output/status, SSH pulls under cron's HOME=/, cron/at permission,
SELinux and key isolation. Verify offline boot and persistence across reboot/OS
update. Existing VMs retain `/var` and may retain old `/etc` unit links/overrides;
this change does not migrate them or repair their checkouts or credentials.

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

- Correct the upstream service/script paths and executable bit using the linked
  development instructions, then build a fresh course disk with `L01_PRIVATE_KEY`
  and complete the workbook guest checks above.

- Build the course OS container and prepare a fresh disk payload from that source;
  verify its channel remains `ics410_l01`.
- On a fresh course installation, check automatic timers are disabled, manual
  updates work, and `ujust toggle-updates` can enable updates.
- Verify a new user's MOTD starts disabled and `ujust toggle-user-motd` can enable
  it; confirm Bazaar's first-login icon and Firefox/CyberChef launching.
- Finish ISO installation and full-bundle capacity/offline application validation.
  Earlier QCOW2 smoke results on main do not establish the current course image's
  behavior. Per-user uv provisioning remains deferred under the shared plan.
