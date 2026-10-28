# ICS410 L01 development

Course-specific build and operation instructions for `ics410_l01`. Follow the
[shared development guide](../../DEVELOPMENT.md) for repository-wide procedures.
Current validation and remaining checks are in [STATUS.md](STATUS.md); accepted
course choices are in [DECISIONS.md](DECISIONS.md).

## Capture and serial device groups

On this branch, ControlThings group setup adds `dialout` alongside `wireshark`
and `usbmon`. This supersedes the shared guide's delegation of serial-group
setup to Aurora's DX tooling. The existing
[startup and manual setup lifecycle](../../DEVELOPMENT.md#controlthings-capture-groups)
still applies: automatic setup targets current `wheel` members; later accounts
and non-administrators can use `ujust controlthings-groups`.

Setup version 2 reapplies membership on the next boot after deploying the updated
image, including systems with a successful version 1 marker. Existing memberships
and group IDs are preserved. Log out completely and log back in after manual
setup, then check `id -nG` for all three groups. See the
[decision](DECISIONS.md#serial-device-group-membership--2026-10-27) and
[validation status](STATUS.md#serial-device-groups--2026-10-27).

## ICS410 L01 workbook

This course-branch feature serves the workbook at `http://localhost/` (IPv4
loopback, port 80) independently of network availability. Its checkout is
`/var/lib/ics410/workbook`. The upstream updater intentionally removes local
changes and untracked files. Its cron runs every six hours and queues an `at` job
with up to 359 minutes of delay.

The image workflow consumes the repository Actions secret `L01_PRIVATE_KEY`.
For local builds, provide a dedicated, unencrypted read-only deploy key outside
the build context:

```bash
sudo env WORKBOOK_SSH_KEY_FILE=/absolute/path/to/workbook-key just build
```

The Actions build also uses its automatically supplied `github.token` for public
GitHub API requests (CyberChef release metadata and workbook SSH host keys).
The workflow writes a private temporary file, passes it as a Podman secret, and
removes it on success or failure. The API token is never retained in the image.
Only `https://api.github.com` receives authentication; redirects are rejected.
Transient HTTP/network errors retry at most twice, respecting numeric Retry-After and
rate-limit reset headers up to 60 seconds per wait. Longer backoffs fail so the
build can be retried later.

Local builds remain anonymous by default. To authenticate, optionally set
`GITHUB_API_TOKEN_FILE` to a nonempty token file outside the build context alongside
`WORKBOOK_SSH_KEY_FILE`. Direct Podman builds can supply
`--secret id=github_token,src=/absolute/path/to/token`. Unlike the workbook deploy
key, this token is only for build-time API access; it does not change workbook Git
SSH authentication. Never put token contents in build arguments or repository files.

The key is intentionally retained in the distributed image and VM, as accepted
for this course. Do not commit it or put it in build arguments. The workflow
writes a temporary mode-0600 file and removes it when the build step exits.
GitHub SSH host keys are retrieved from its HTTPS metadata endpoint during the
build. A fresh clone of the remote default branch is required on each `just build`;
clone or resource validation failures stop the build. Direct Podman builds must
supply `--secret id=workbook_key,src=...` and a fresh `WORKBOOK_BUILD_EPOCH` argument.

The build accepts resources under `resources/` or `docs/resources/`, validates
required files and `User=ics410-workbook-update`, and enables the upstream
`ewb-update.service` by absolute path. The service and cron file contents remain
unchanged; there is no platform service override. Both cron and at daemons are
enabled. The platform web service is `ewb-webserver.service`.

The complete Git checkout (including `.git`), credentials and initial user crontab
are populated during image creation. There is no seed archive or boot initializer.
OS updates preserve the existing `/var` state; they do not provision a missing
workbook or repair one. This feature therefore requires a newly created disk
installation, or separate manual provisioning for an existing installation.

`ics410-workbook-update` owns the checkout and uses SSH configuration under
`/var/lib/ics410/workbook-update/.ssh`. Local Git `core.sshCommand` selects this
configuration explicitly, including for cron with HOME=/. The web account cannot
access credentials or `.git`.

Any local user can run `workbook-update`, with optional upstream arguments such
as `-verbose`, without a password. `/usr/bin/workbook-update` is the root-owned
launcher. It uses noninteractive sudo to run
the discovered upstream `workbook-update.sh` through `/bin/bash` as
`ics410-workbook-update`, even when Git restores script mode 0644.
Sudoers permits exactly five argument forms: no flags, `-verbose`, `-debuglog`,
and both flags in either order. Other arguments and repeated flags are no longer
authorized. It grants no environment override privilege or other commands. Arguments, stdout, stderr and exit status pass
through; the launcher adds no logging, redirection or locking. Upstream controls
option handling and concurrency between users, cron and systemd. Its destructive
update policy applies to manual invocations too.

### Changes required in the workbook repository

Ensure the upstream `ewb-update.service` has these settings in its existing
`[Service]` section (use `docs/resources` instead of `resources` if that is the
repository's actual layout):

```ini
User=ics410-workbook-update
WorkingDirectory=/var/lib/ics410/workbook
ExecStart=/bin/bash /var/lib/ics410/workbook/resources/workbook-update.sh
```

Remove shell redirection such as `> /dev/null` from `ExecStart`. To suppress
service stdout, add `StandardOutput=null`; otherwise leave normal journal output.
These service settings do not affect output from manual script invocations.
Keep the upstream boot enablement, for example `WantedBy=multi-user.target` in
`[Install]`. Do not depend on `ics410-workbook-init.service`.

Ensure paths inside the script and cron file use `/var/lib/ics410/workbook`.
Cron and systemd should invoke the upstream script through `/bin/bash` as the
updater account, rather than calling the user launcher. Commit the script's executable
bit upstream (`git update-index --chmod=+x <path-to-workbook-update.sh>`) if
other callers execute it directly. The platform sets it executable during image
creation, but the user launcher no longer relies on that mode.
Implement any concurrency protection inside the upstream script.

The user supplied the upstream updater script during diagnosis; its unconditional
`git reset --hard` explains loss of a locally applied executable bit. The deployed
cron and service files still need guest verification.

### Guest checks and operations

```bash
systemctl status ewb-webserver ewb-update crond atd
curl --fail http://127.0.0.1/
workbook-update -verbose
sudo crontab -u ics410-workbook-update -l
sudo -u ics410-workbook-update atq
journalctl -u ewb-update -u ewb-webserver
```

After an upstream service-definition update, run `sudo systemctl daemon-reload`;
restart it if immediate execution is desired. Re-enable the absolute unit path
if its `[Install]` section changes. There is no platform boot-time reload hook.
Key rotation for existing installations requires explicit provisioning; rebuilding
an image does not overwrite their persistent key.

These changes do not migrate existing VMs: their `/var` checkout, installed cron,
and `/etc` service links or overrides may retain earlier configuration. Inspect
those separately when validating an upgraded VM; fresh disks are the installation
path covered by this design.

Local checks: `python3 tests/check_workbook.py` and
`python3 tests/check_workflow_tags.py`. See [course status](STATUS.md)
for actual validation and remaining VM checks.
