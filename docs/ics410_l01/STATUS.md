# ICS410 L01 current status

## Current baseline — 2026-10-17

- Course HEAD at extraction: `c685367`, the completed merge of main's `8952b79`
  MOTD change. Earlier main integration is `6e1e987`. Shared implementation and
  validation history live in [shared status](../STATUS.md); course choices live
  in [course decisions](DECISIONS.md).
- Course differences: `DEFAULT_TAG=ics410_l01` (`64dfa77`), normal Aurora stable
  with explicit Incus/agent/LXC RPMs (`af3091b`), and disabled automatic-update
  defaults (`a1b1733`). The course README currently also contains an automatic
  update section; it is preserved by this four-file extraction.
- Brewfile currently matches main: 29 formulae and 16 AMD64 Flatpaks (15 on ARM64,
  where ZAP is excluded). These counts supersede the earlier six-Flatpak notes;
  the additional selected Aurora apps were included in `6d17d8c` on main.
- Documentation now separates course records from shared records. Shared
  DECISIONS.md and STATUS.md are restored byte-for-byte from local main at
  `8952b79`; their historical wording is retained to preserve exact agreement.
  This documentation change is uncommitted.

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

- Build the course OS container and prepare a fresh disk payload from that source;
  verify its channel remains `ics410_l01`.
- On a fresh course installation, check automatic timers are disabled, manual
  updates work, and `ujust toggle-updates` can enable updates.
- Verify a new user's MOTD starts disabled and `ujust toggle-user-motd` can enable
  it; confirm Bazaar's first-login icon and Firefox/CyberChef launching.
- Finish ISO installation and full-bundle capacity/offline application validation.
  Earlier QCOW2 smoke results on main do not establish the current course image's
  behavior. Per-user uv provisioning remains deferred under the shared plan.
