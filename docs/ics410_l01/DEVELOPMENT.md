# ICS410 L01 development

Course-specific build and operation instructions for `ics410_l01`. Follow the
[shared development guide](../../DEVELOPMENT.md) for repository-wide procedures.
Current validation and remaining checks are in [STATUS.md](STATUS.md); accepted
course choices are in [DECISIONS.md](DECISIONS.md).

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

The key is intentionally retained in the distributed image and VM, as accepted
for this course. Do not commit it or put it in build arguments. The workflow
writes a temporary mode-0600 file and removes it when the build step exits.
GitHub SSH host keys are retrieved from its HTTPS metadata endpoint during the
build. A fresh clone of the remote default branch is required on each `just build`;
clone or resource validation failures stop the build. Direct Podman builds must
supply `--secret id=workbook_key,src=...` and a fresh `WORKBOOK_BUILD_EPOCH` argument.

The build accepts resources under `resources/` or `docs/resources/`, validates
required files and `User=ics410-workbook-update`, and links `/usr/bin/workbook-update`
to the discovered script. The repository's own internal paths must match its
layout. The update unit remains linked into the checkout. Its platform drop-in
sets ExecStart without shell-redirection tokens. Both cron and at daemons are
enabled; no extra systemd update timer is installed.

`ics410-workbook-update` owns the checkout and uses SSH configuration under
`/var/lib/ics410/workbook-update/.ssh`. Local Git `core.sshCommand` selects this
configuration explicitly. The web account has no access to credentials, `.git`,
or the root-only seed. Image seeding fills absent state and installs the user
crontab once; it never replaces an existing checkout/key during OS updates.
The upstream updater may replace its dedicated user's crontab after a pull.

Useful guest checks and operations:

```bash
systemctl status ics410-workbook-web ewb-update crond atd
curl --fail http://127.0.0.1/
sudo -u ics410-workbook-update workbook-update -verbose
sudo crontab -u ics410-workbook-update -l
sudo -u ics410-workbook-update atq
journalctl -u ics410-workbook-init -u ewb-update -u ics410-workbook-web
```

After an upstream service-definition update, run `sudo systemctl daemon-reload`;
restart it if immediate execution is desired. Re-enable the absolute unit path
if its [Install] section changes. Initialization reloads systemd at each boot.
The built seed revision is in `/usr/share/ics410-workbook/revision` (root access).
Key rotation for existing installations requires explicit provisioning; rebuilding
an image does not overwrite their persistent key.

Local checks: `python3 tests/check_workbook.py` and
`python3 tests/check_workflow_tags.py`. See [course status](STATUS.md)
for the actual validation and remaining VM checks.
