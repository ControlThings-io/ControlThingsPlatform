# Current status

## Dependabot assessment — 2026-10-14

Reviewed local main at `8a3e74f` and open Dependabot PRs
[#3](https://github.com/ControlThings-io/ControlThingsPlatform/pull/3),
[#8](https://github.com/ControlThings-io/ControlThingsPlatform/pull/8), and
[#9](https://github.com/ControlThings-io/ControlThingsPlatform/pull/9).
PR #3's local branch now includes the shared tag fix and the dependency updates
from PRs #8 and #9 in one working tree, as requested for a combined commit.
No remote comments, reruns, merges, commits, or pushes performed. Remote PR
branches have not been updated; a combined local commit does not update all PRs.

### Combined local fix and validation

- Working branch: `dependabot/github_actions/docker/login-action-4.6.0`, based
  on PR head `f66e6aa`. This branch predates main's latest changes; it has not
  been rebased onto `8a3e74f`.
- The container workflow now uses `pr-<number>` tags on pull request events.
  Main still uses the configured default tag; course branches retain their tags.
- Added PR #8's builder pin `028e4d2` and PR #9's upload-artifact 7.0.2 pin
  `cf430e0` to `.github/workflows/build-disk.yml`. Login 4.6.0 is already in the
  branch's HEAD. The shared tag fix covers all three PR numbers once present in
  the branch being tested; it does not require separate per-PR tag logic.
- Added `tests/check_workflow_tags.py`. Run it from the repository root with
  `python3 tests/check_workflow_tags.py`. All eight event/ref cases passed,
  including PRs #3/#8/#9, main push/schedule/manual dispatch, and course refs.
  Checks exercise the workflow shell, alias tag generation, actual build recipe
  arguments using mocked Podman, and build/rechunk shell syntax. The original
  slash-containing PR tags are rejected by the tag grammar check.
- `just check` passed with a temporary writable `XDG_RUNTIME_DIR` because the
  sandbox's default runtime directory is read-only. `git diff --check` passed.
- Full image build/rechunk integration remains blocked locally: rootful Podman
  requires a sudo password. These local checks do not establish GitHub CI or
  login-action runtime success.
- Next: reconcile this older branch with main before submitting the combined
  updates, then run GitHub Actions build/rechunk checks. The disk-workflow
  coverage and runner issues below remain outstanding. Login remains skipped on
  PR events and needs validation in an authorized publishing run.

### Evidence

- Root cause traced to project commit
  [334bf00](https://github.com/ControlThings-io/ControlThingsPlatform/commit/334bf0008bcf101a7c20f138f048768463ed0ddf)
  (`build: now builds ics410 branches`, 2026-08-31). It replaced unconditional
  `just generate-default-tag` with a main/non-main conditional that uses
  `GITHUB_REF_NAME` as the tag for every non-main event, including PRs.
  GitHub sets that variable to `<number>/merge` for PR events. This is a project
  customization regression, not an invalid Dependabot branch name. Git history
  identifies the commit, but does not establish whether an assistant drafted it.
- The initial repository commit `62bc1b1` used the configured default tag for
  PRs. GitHub repository metadata identifies `ublue-os/image-template` as the
  source template. Its current container workflow, inspected on 2026-10-14,
  still uses unconditional `just generate-default-tag`. Aurora DX supplies the
  base image; it does not supply or execute this repository's modified workflow.
- All three container builds and Just syntax checks passed. Rechunking failed
  with `invalid reference format` for image tags `3/merge`, `8/merge`, and
  `9/merge`, respectively. The Default Tag step in
  `.github/workflows/build.yml` copies `GITHUB_REF_NAME` into the tag on PRs.
- Reviewed jobs:
  [#3](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/33455687467/job/99695046213),
  [#8](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/37185090607/job/111385250770),
  [#9](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/38120655835/job/114414514751).
  None executed the updated action. Only the container workflow ran for these
  PR heads; the disk workflow did not run.
- Main's scheduled container build
  [38584995397](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/38584995397)
  succeeded on 2026-10-14 at `8a3e74f`; this does not validate the PR dependencies.
- Disk workflow path filters include leading `./`; GitHub path filters match
  repository-relative paths. The runner expression also defaults PRs to ARM
  because `inputs.platform` is absent, while ARM dependency installation is
  conditional on an explicit `arm64` input.
- PR #8's upstream source diff adds a deprecation warning and retains the action
  inputs/outputs. Upstream recommends `osbuild/image-builder-action`, whose
  interface differs; migration requires separate review and disk/ISO checks.

### Recommendations and remaining validation

These are proposals, not accepted implementation decisions:

1. Validate and submit the local PR tag fix, preserving existing main and course
   branch tags. Rebase the dependency PRs after that fix, then rerun CI.
2. Remove leading `./` from disk workflow path filters and default PR builds to
   amd64 explicitly. Verify QCOW2 and Anaconda ISO builds on the updated builder.
3. PR #3 (login 4.6.0) and #9 (upload 7.0.2) look suitable to merge after the
   workflow repair and relevant validation. Login and upload remain deliberately
   skipped on PR events; validate their behavior in an authorized publishing or
   artifact-upload run. PR #3 has automatic rebases disabled due to age.
4. PR #8 can serve as an interim update after disk builds pass; plan migration
   from the deprecated builder separately, preserving required ISO features.

No real local image builds or new remote runs were performed. Updated login,
upload, and disk-builder runtime behavior remains unverified.
