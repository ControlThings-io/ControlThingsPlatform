# ICS410 L01 current status

## Serial device groups — 2026-10-27

- Added `dialout` alongside `wireshark` and `usbmon` for automatic setup of current
  `wheel` members and explicit manual setup. Version 2 reapplies the policy to
  existing administrators after deployment; existing memberships and vendor GIDs
  are preserved. See [operation guidance](DEVELOPMENT.md#capture-and-serial-device-groups)
  and [decision](DECISIONS.md#serial-device-group-membership--2026-10-27).
- Passed `python3 tests/check_controlthings_groups.py`: real isolated group tools
  checked all wheel users, explicit non-administrator setup, preserved vendor
  GIDs/memberships, version 1 migration, repeat runs, empty-wheel deferral and
  failure handling; recipe delegation uses mocked pkexec. Bash syntax, Just
  formatting, `systemd-analyze verify` and whitespace/link review passed.
  Group-tool and systemd checks required execution outside the default sandbox
  because it restricts audit/socket access; account mutations stayed inside
  temporary Bubblewrap fixtures.
- No image build, remote CI or guest/hardware validation performed. Next: verify
  fresh-install and version 1 upgrade boots, effective login groups, KDE pkexec
  and serial-device access in a guest. Propagation to main remains outstanding;
  shared documentation is unchanged on this branch.

## Current work — 2026-10-24

Workbook simplification is committed as `6a5f8c2`; main's authentication and
reliability changes were merged as `39504c2`. Workbook API authentication is committed as `e24710a`. Shared history remains in
[shared status](../STATUS.md); accepted course choices are in
[course decisions](DECISIONS.md).

- Container run [40080883375](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/40080883375)
  at `1626d43` passed checkout and the OS image build, then failed before Chunkah
  execution: Quay returned HTTP 503 for the pinned builder manifest. Repacking,
  publication and signing did not complete. A later live Skopeo metadata request
  resolved the same AMD64 builder digest successfully; no pin change is needed.
  The first repair (`19b2528`) failed in
  [run 40081854831](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/40081854831)
  with `unknown flag: --retry`. The runner's Podman 4.9.3 also lacks pull's
  `--policy` flag; the mocked regression had not checked CLI compatibility.
  The corrected recipe uses plain `podman pull` with at most three invocations,
  five seconds apart; Podman's own internal retries remain enabled. Chunkah runs
  once with `--pull=never`; exhausted pulls stop before repacking/import/retagging,
  and all failure paths retain temporary-file cleanup.
  CI now runs `tests/check_rechunk.py` before the image build. The fixture parses
  each Podman command with the installed CLI's `--help` before simulating it,
  placing help before the image name so it cannot become a container argument.
  Extracted Ubuntu package `podman_4.9.3+ds1-1ubuntu0.2_amd64.deb` reproduced both
  unsupported-flag errors and passed the corrected fixture, as did host Podman.
  Checks cover three source tags, transient recovery, exhausted retries, all six
  failure stages and cleanup. Registry-login/workflow-tag regressions, Just/Bash
  syntax and whitespace checks also passed. CLI parsing is real; container/image
  operations and retry waits are mocked. No full local build or remote CI rerun
  was performed for this correction. Next: submit when authorized, rerun container
  CI and verify repacking/publication/signing before preparing a fresh disk payload.

- Explicit Bash invocation is committed as `73db909`. The launcher is now
  installed directly at `/usr/bin/workbook-update` (uncommitted cleanup), replacing
  the libexec symlink. Checks verify a regular executable file and no libexec copy.
  Sudoers allows the exact script with no flags, either supported flag, or both
  orders. Guest evidence: direct invocation failed at mode 0644; chmod allowed
  one successful update, which restored 0644. The supplied upstream script runs
  Git reset before checking for updates. Regression fixtures reproduce that reset
  and verify Bash execution, output/status forwarding and exact policy generation
  for both resource layouts. Workbook checks, real visudo syntax validation,
  Bash syntax and whitespace review passed locally. Sudo execution remains mocked;
  real VM authorization, repeated updates and flag combinations remain pending.
- Reconciled the authentication stash with the merged shared implementation.
  The workbook build step now mounts `github_token` and uses the shared API
  helper for GitHub SSH host-key metadata. The API token is temporary; the
  separately retained workbook SSH deploy key still handles clone/runtime pulls.
  Local API authentication remains optional. The original stash is retained as
  a backup; its older shared helper was not restored over main's retry changes.
- Current checks passed: `tests/check_workbook.py`, `tests/check_github_api.py`,
  `tests/check_http_download.py`, `tests/check_registry_login.py`,
  `tests/check_workflow_tags.py`, Just/Bash syntax and whitespace review.
  Workbook fixtures execute the real API helper with only network transport
  mocked, checking authenticated and anonymous metadata lookup, both resource
  layouts, credential separation, output and build-secret mounts. No live
  authenticated request, private-repository fetch, image build or remote CI run
  was performed. Prior merge checks also passed CyberChef installation tests.

- Workbook and retained deploy-key credentials are populated only during image
  creation. Removed seed archive creation, boot initialization and its unit.
  Existing `/var` state persists; missing checkouts are not provisioned on OS update.
- Removed the platform `ewb-update.service` override. The upstream service remains
  linked and unchanged. Upstream must correct its ExecStart redirection and paths;
  required settings are in [course development](DEVELOPMENT.md#changes-required-in-the-workbook-repository).
  User reports the upstream service updated; deployed paths still need guest
  verification. The user supplied the updater script for the current diagnosis.
- `/usr/bin/workbook-update` is a root-owned launcher using passwordless,
  noninteractive sudo for Bash with only the upstream script as
  `ics410-workbook-update` and the supported flag combinations.
  Arguments, stdout, stderr and exit status pass through. The complete `.git`
  directory remains in the checkout; credentials and metadata retain restricted
  ownership. Cron/systemd should invoke the upstream script through Bash. Concurrency belongs
  upstream, with no platform lock.
- Renamed the platform web unit to `ewb-webserver.service`. It still serves
  `/var/lib/ics410/workbook` at IPv4 localhost port 80 as a separate web account.
- The updater's executable correction was committed as `8f3b701`; build-time chmod
  remains. The user launcher now tolerates Git restoring mode 0644; direct
  callers still need the upstream executable bit or explicit Bash invocation.
- Firefox homepage remains `http://localhost/` (`5934cee`), with inherited editable
  shortcuts/defaults. Course uses standard Aurora pinned to `stable-20261022.1`
  (`b7d37dc`), with existing RPM selections and OS automatic-update defaults disabled.
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

Historical local checks for the simplification committed as `6a5f8c2` passed:
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

- Validate both API lookups in a container build. Verify the new launcher in a VM
  with script mode 0644, all five permitted flag forms and rejection of unknown
  flags; run two successive updates. Build a fresh course disk and complete the
  guest checks above, including the user-reported upstream service correction.

- Complete container repacking/publication, then prepare a fresh disk payload;
  verify its channel remains `ics410_l01`.
- On a fresh course installation, check automatic timers are disabled, manual
  updates work, and `ujust toggle-updates` can enable updates.
- Verify a new user's MOTD starts disabled and `ujust toggle-user-motd` can enable
  it; confirm Bazaar's first-login icon and Firefox/CyberChef launching.
- Finish ISO installation and full-bundle capacity/offline application validation.
  Earlier QCOW2 smoke results on main do not establish the current course image's
  behavior. Shared uv provisioning follows the merged
  [shared implementation](../STATUS.md#current-work); course guest coverage remains.
