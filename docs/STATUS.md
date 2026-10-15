# Current status

## Container size comparison — 2026-10-15

- Added executable `scripts/compare-image-sizes.sh OLD_TAG NEW_TAG` to query
  ControlThings GHCR layer metadata and report compressed totals and size growth.
  Usage and limitations are in [README.md](../README.md#building-disk-images).
- Validation: Bash syntax and `git diff --check` passed. With mocked Skopeo
  responses and real jq/awk, checked growth, shrinkage, equal sizes, invalid
  arguments, incomplete metadata, and registry failure propagation.
- No live GHCR comparison performed; next step is running against two published
  tags with Skopeo available. ShellCheck is unavailable locally.

## Disk-image testing — 2026-10-14

The user reports that the disk-image build succeeded and is downloading the
artifact for additional testing. The workflow run, source image revision, and
artifact format have not yet been recorded; this report does not establish ISO
or offline-installation success.

- Pending: boot/install the downloaded artifact in a VM, verify first login,
  default desktop and lock-screen backgrounds, and persistence of user choices.
- Offline classroom validation: repeat installation and first login with the
  VM network adapter disconnected, then run the required training tools.
- Classroom account provisioning, managed home content, and bundled offline
  Python/Homebrew dependencies remain proposals, not implemented features.

## Default lock-screen background — 2026-10-14

Committed on `main` in `9cd857d`. At this review, local `main` matches the
locally recorded `origin/main`.

- Added a system-default `kscreenlockerrc` through the `system_files/` overlay,
  selecting `CT-Aquila-Aurea-Machina` per the user's corrected choice. The
  desktop remains `CT-De-Machina-Logica-Programmabilis`. The existing build
  script installs it; no new login/autostart script is needed.
- Individual user settings remain higher priority. Existing users who inherit
  system defaults can see the new background. Lock timing, authentication, and
  the pre-login screen are unchanged.
- Updated usage and rationale in [README.md](../README.md#default-lock-screen-background)
  and [DECISIONS.md](DECISIONS.md#default-lock-screen-background--2026-10-14).
- Validation passed using real `kreadconfig6`/`kwriteconfig6` against temporary
  system/user directories: fresh configuration reads the image plugin, image,
  and preview defaults; a saved user image takes precedence without modifying
  system defaults. Verified the bundled asset path and absence of lock-timing
  or password-policy settings. `git diff --check` passed.
- Remaining validation: build/deploy the image, lock a fresh user's session,
  and verify both the default image and persistence of a user's chosen image
  through lock/unlock and logout/login. No visual lock-screen test performed.

## Default desktop wallpaper — 2026-10-14

Committed on `main` in `560984f`. The user selected
`CT-De-Machina-Logica-Programmabilis` as the default wallpaper for new users.

### Implemented

- `build_files/plasma-desktop.js` selects the existing wallpaper package when
  Plasma creates a Folder View desktop. It uses the package directory so Plasma
  can choose an image suited to the screen size.
- `build_files/build.sh` installs that single script into Aurora's dark and light
  theme setup directories after package installation. Missing directories fail
  the build rather than silently dropping the customization.
- Aurora's other theme and panel settings remain inherited. Saved desktops are
  not rewritten by a login script. New desktops on additional monitors or
  activities also receive the default while an Aurora global theme is active.
- Usage and fresh-user verification are in
  [README.md](../README.md#default-desktop-wallpaper); rationale is in
  [DECISIONS.md](DECISIONS.md#default-desktop-wallpaper--2026-10-14).

### Validation

- `bash -n build_files/build.sh` and `node --check build_files/plasma-desktop.js`
  passed.
- Executed the real JavaScript using a mocked Plasma applet API. Verified the
  image plugin, configuration group/key, reload, installed package ID, and PNG
  signatures for all three image variants.
- Executed the build installation loop against temporary theme directories:
  both received the identical script with mode 0644. Removing one expected
  directory caused the loop to fail as intended.
- `git diff --check` passed.
- Inspected the host's Aurora theme setup hooks and KDE's `ShellCorona` source:
  the hook is invoked on containment creation. The host files are evidence for
  the implementation, not proof of the exact contents of a future stable image.
- No image build, deployment, or live Plasma login test performed for this work.

### Next steps

1. Build the image and verify both expected theme hooks are installed.
2. In a VM running that image, sign in with a fresh user and check the default
   wallpaper. Change it, log out/in, and verify the selection persists.
3. Verify a pre-existing user's selected wallpaper is preserved, plus the default
   on newly created desktops and Aurora's light-theme variant.
4. Push only when requested. Login-screen and installer branding are separate
   future work; no changes to those surfaces are included here.

## Dependency workflow follow-up

The combined dependency updates and PR image-tag fix are now on `main` in
`ecc50dc` (PR #3). The user confirmed on 2026-10-14 that the combined PR #3
workflow passed. The previously recorded CI run
[38663972331](https://github.com/ControlThings-io/ControlThingsPlatform/actions/runs/38663972331)
passed build, rechunking, and tagging at PR head `5b4bff6`. Registry login,
publishing, and signing were skipped on the PR event. The old PR tag regression
originated in project commit `334bf00`, which used `GITHUB_REF_NAME` for every
non-main event, including slash-containing PR merge refs.

Superseded PRs #8 and #9 are closed, as confirmed by the user on 2026-10-14.

Outstanding work:

- Disk workflow path filters still include leading `./` and the runner expression
  defaults PRs to ARM while skipping ARM dependency installation.
- A disk-image build succeeded per the user's report above. Record the workflow
  run and artifact details; publishing behavior and untested artifact formats
  still need validation.
- Upstream deprecated `osbuild/bootc-image-builder-action`; migration to its
  replacement requires separate input/output and ISO-feature review.
