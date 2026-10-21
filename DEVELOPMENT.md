# Development guide

Build, customize, and validate ControlThings Platform. For the project overview
and user commands, see [README.md](README.md). Current work and validation gaps
are in [docs/STATUS.md](docs/STATUS.md); accepted choices are in
[docs/DECISIONS.md](docs/DECISIONS.md).

For a long-lived variant branch, use `docs/<branch>/STATUS.md` and
`docs/<branch>/DECISIONS.md` for variant-only work. Shared documents follow main.
Keep user-facing usage in README and link here for build details.

The fork-setup instructions below originated in Universal Blue's image template.
This repository is already configured; maintainers normally start with
[repository contents](#repository-contents) or [disk builds](#building-disk-images).

# Community

If you have questions about this template after following the instructions, try the following spaces:
- [Universal Blue Forums](https://universal-blue.discourse.group/)
- [Universal Blue Discord](https://discord.gg/WEu6BdFEtp)
- [bootc discussion forums](https://github.com/bootc-dev/bootc/discussions) - This is not an Universal Blue managed space, but is an excellent resource if you run into issues with building bootc images.

# How to Use

To get started on your first bootc image, simply read and follow the steps in the next few headings.
If you prefer instructions in video form, TesterTech created an excellent tutorial, embedded below.

[![Video Tutorial](https://img.youtube.com/vi/IxBl11Zmq5w/0.jpg)](https://www.youtube.com/watch?v=IxBl11Zmq5wE)

## Step 0: Prerequisites

These steps assume you have the following:
- A Github Account
- A machine running a bootc image (e.g. Bazzite, Bluefin, Aurora, or Fedora Atomic)
- Experience installing and using CLI programs

## Step 1: Preparing the Template

### Step 1a: Copying the Template

Select `Use this Template` on this page. You can set the name and description of your repository to whatever you would like, but all other settings should be left untouched.

Once you have finished copying the template, you need to enable the Github Actions workflows for your new repository.
To enable the workflows, go to the `Actions` tab of the new repository and click the button to enable workflows.

### Step 1b: Cloning the New Repository

Here I will defer to the much superior GitHub documentation on the matter. You can use whichever method is easiest.
[GitHub Documentation](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)

Once you have the repository on your local drive, proceed to the next step.

## Step 2: Initial Setup

### Step 2a: Creating a Cosign Key

Container signing is important for end-user security and is enabled on all Universal Blue images. By default the image builds *will fail* if you don't.

First, install the [cosign CLI tool](https://edu.chainguard.dev/open-source/sigstore/cosign/how-to-install-cosign/#installing-cosign-with-the-cosign-binary)
With the cosign tool installed, run inside your repo folder:

```bash
COSIGN_PASSWORD="" cosign generate-key-pair
```

The signing key will be used in GitHub Actions and will not work if it is password protected.

> [!WARNING]
> Be careful to *never* accidentally commit `cosign.key` into your git repo. If this key goes out to the public, the security of your repository is compromised.

Next, you need to add the key to GitHub. This makes use of GitHub's secret signing system.

<details>
    <summary>Using the Github Web Interface (preferred)</summary>

Go to your repository settings, under `Secrets and Variables` -> `Actions`
![image](https://user-images.githubusercontent.com/1264109/216735595-0ecf1b66-b9ee-439e-87d7-c8cc43c2110a.png)
Add a new secret and name it `SIGNING_SECRET`, then paste the contents of `cosign.key` into the secret and save it. Make sure it's the .key file and not the .pub file. Once done, it should look like this:
![image](https://user-images.githubusercontent.com/1264109/216735690-2d19271f-cee2-45ac-a039-23e6a4c16b34.png)
</details>
<details>
<summary>Using the Github CLI</summary>

If you have the `github-cli` installed, run:

```bash
gh secret set SIGNING_SECRET < cosign.key
```
</details>

### Step 2b: Choosing Your Base Image

To choose a base image, simply modify the line in the container file starting with `FROM`. This will be the image your image derives from, and is your starting point for modifications.
For a base image, you can choose any of the Universal Blue images or start from a Fedora Atomic system. Below this paragraph is a dropdown with a non-exhaustive list of potential base images.

<details>
    <summary>Base Images</summary>

- Bazzite: `ghcr.io/ublue-os/bazzite:stable`
- Aurora: `ghcr.io/ublue-os/aurora:stable`
- Bluefin: `ghcr.io/ublue-os/bluefin:stable`
- Universal Blue Base: `ghcr.io/ublue-os/base-main:latest`
- Fedora: `quay.io/fedora/fedora-bootc:44`

You can find more Universal Blue images on the [packages page](https://github.com/orgs/ublue-os/packages).
</details>

If you don't know which image to pick, choosing the one your system is currently on is the best bet for a smooth transition. To find out what image your system currently uses, run the following command:
```bash
sudo bootc status
```
This will show you all the info you need to know about your current image. The image you are currently on is displayed after `Booted image:`. Paste that information after the `FROM` statement in the Containerfile to set it as your base image.

### Step 2c: Changing Names

Change the `IMAGE_NAME` and `REPO_ORGANIZATION` variable inside the `image-template.env`

To commit and push all the files changed and added in step 2 into your Github repository:
```bash
git add Containerfile image-template.env cosign.pub
git commit -m "Initial Setup"
git push
```
Once pushed, go look at the Actions tab on your Github repository's page.  The green checkmark should be showing on the top commit, which means your new image is ready!

## Step 3: Switch to Your Image

From your bootc system, run the following command substituting in your Github username and image name where noted.
```bash
sudo bootc switch ghcr.io/<username>/<image_name>
```
This should queue your image for the next reboot, which you can do immediately after the command finishes. You have officially set up your custom image! See the following section for an explanation of the important parts of the template for customization.

# Repository Contents

## Default desktop wallpaper

New users start with **De Machina Logica Programmabilis** on Aurora's KDE
desktop. Existing desktops keep their selected wallpaper. New desktops created
for additional monitors or activities also use this default while an Aurora
global theme is selected.

The wallpaper images and metadata live in
[`system_files/usr/share/wallpapers/CT-De-Machina-Logica-Programmabilis/`](system_files/usr/share/wallpapers/CT-De-Machina-Logica-Programmabilis/).
[`build_files/plasma-desktop.js`](build_files/plasma-desktop.js) selects that
package. To choose another bundled wallpaper, change the package directory in
its `Image` setting, keeping the absolute `/usr/share/wallpapers/` path.
[`build_files/build.sh`](build_files/build.sh) installs this setup script into
Aurora's dark and light global themes when building the image.

Rebuild and deploy the image, then test with a fresh user profile. Verify that
the wallpaper appears, a user-selected replacement survives logout/login, and
an existing user's wallpaper stays unchanged. This setting controls desktop
wallpaper; login-screen and installer branding are configured separately.

## Default lock-screen background

The lock screen defaults to **Aquila Aurea Machina** through
[`system_files/usr/share/kde-settings/kde-profile/default/xdg/kscreenlockerrc`](system_files/usr/share/kde-settings/kde-profile/default/xdg/kscreenlockerrc).
To select another bundled wallpaper, change both `Image` and `PreviewImage` to
its package directory using a `file:///usr/share/wallpapers/` URL.
The existing build script copies this file into Aurora's system configuration.

Users who have saved their own lock-screen background keep that choice. Existing
users who still inherit the system default may also see the new background.
After deploying a rebuilt image, lock a fresh user's session to check it, then
choose another background in Plasma's Screen Locking settings and verify that
the choice survives another lock and a logout/login. This does not change the
login screen shown before signing in, or locking and password requirements.

## Default login-screen background

The Plasma Login Manager login screen defaults to **Aquila Aurea Machina**.
[`build_files/build.sh`](build_files/build.sh) updates only `Image` and
`PreviewImage` in the `[Greeter][Wallpaper][org.kde.image][General]` group of
Aurora's `/usr/lib/plasmalogin/defaults.conf`, preserving other inherited settings.
Both values select `file:///usr/share/wallpapers/CT-Aquila-Aurea-Machina/`.
The build requires the inherited defaults file and bundled wallpaper assets.

Administrator settings in `/etc/plasmalogin.conf` take precedence. Existing
installations that inherit the distribution default receive it through an image
update and reboot. To select another bundled wallpaper, change `login_wallpaper`
and its asset checks in the build script. Desktop and lock-screen settings are
configured separately as described above.

After deployment, verify the initial login screen and logout screen, cropping on
normal and ultrawide displays, and persistence across an image update. Also check
that an explicit local wallpaper override continues to take precedence.

## Terminal MOTD default

New users start with Aurora's terminal message of the day disabled. The image
seeds `/etc/skel/.config/no-show-user-motd`, using Aurora's existing preference
marker. Run `ujust toggle-user-motd` to enable or disable it afterward.
Existing users keep their preference. The custom Macchina display in the
ControlThings fish configuration remains enabled.

Rebuild the OS container and prepare a fresh disk payload to include this default.
Verify with a newly created user that Aurora's MOTD is absent, then enable it
with `ujust toggle-user-motd` and open a new terminal to confirm it appears.

## ControlThings capture groups

ControlThings follows Aurora's one-time startup setup pattern for the
`wireshark` and `usbmon` groups. On the first boot where `wheel` has members,
`controlthings-groups.service` adds all those administrator accounts to both
capture groups, preserving their primary and other supplementary groups.
Existing administrator accounts are included when first deploying this feature.

The shared [controlthings-groups script](system_files/usr/libexec/controlthings-groups)
records its successful setup version in `/etc/ublue/controlthings-groups` and
skips later automatic runs at that version. Increment `GROUP_SETUP_VER` when a
future policy change should reapply setup. An empty `wheel` group or failed setup
does not record the new version; failures retry through systemd, and empty membership
is checked again at the next boot.

For accounts created later, or for a non-administrator login account, run this as
the user whose memberships should be updated:

```bash
ujust controlthings-groups
```

Authorize the request, then log out completely and log back in. The
[recipe](system_files/usr/share/ublue-os/just/60-custom.just) calls the same script
with `--user USER`, bypassing the startup marker without changing it. Check the
result with `id -nG` in a new session. Administrators can also explicitly run
`sudo /usr/libexec/controlthings-groups --user USERNAME` for another local account.

`dialout` remains available through Aurora's existing `ujust dx-group` command;
ControlThings does not manage it. Capture/device permissions still depend on
Wireshark's package configuration and the available hardware. See
[validation status](docs/STATUS.md#validation-evidence) and
[decision](docs/DECISIONS.md#controlthings-capture-groups--2026-10-15).

## CyberChef offline application

CyberChef is bundled at `/usr/share/cyberchef/` and appears as **CyberChef** in
the Utilities and Development menus. Its launcher uses the bundled Firefox RPM to open
`file:///usr/share/cyberchef/index.html`. No webserver or runtime download is required.
The bundled upstream icon is installed in the standard hicolor icon theme.

Each `just build` resolves the latest stable
[official CyberChef release](https://github.com/gchq/CyberChef/releases/latest),
downloads its offline ZIP, and verifies the asset's published SHA-256. A separate
Containerfile step refreshes CyberChef without invalidating the package-install
step. Direct Podman builds should pass a fresh
`--build-arg CYBERCHEF_BUILD_EPOCH="$(date -u +%s%N)"` to request the same refresh
behavior; otherwise normal layer caching applies.

GitHub Actions authenticates the release API lookup with the job's temporary
`github.token`. The workflow writes a mode-0600 temporary file, passes it through
an optional Podman secret mount, and deletes it on success or failure. Token
contents are not passed as build arguments, logged, or retained in the image.
Only `https://api.github.com` receives authentication; API redirects are rejected.
The shared [API helper](build_files/github_api.py) retries transient HTTP errors
at most twice, respecting numeric Retry-After and rate-limit reset headers up to
60 seconds per wait. Longer backoffs fail for a later build retry. The shared
[download helper](build_files/http_download.py) applies the same retry policy to
the ZIP and license, including network timeouts and incomplete transfers. Each
retry restarts the download; checksum validation still applies. Asset and license
downloads do not receive the API token.

Eligible publishing jobs authenticate to GHCR before building. The existing
Docker login supports signing; rootful Podman uses a separate temporary auth file
through `REGISTRY_AUTH_FILE` for pulls and pushes. An `always()` cleanup step
removes that file. Pull requests retain the existing anonymous registry behavior.

Local builds remain anonymous unless `GITHUB_API_TOKEN_FILE` points to a nonempty
token file outside the build context. For example:

```bash
sudo env GITHUB_API_TOKEN_FILE=/absolute/path/to/token just build
```

Direct Podman builds can supply
`--secret id=github_token,src=/absolute/path/to/token`. Never commit the token
file. Local authentication/cleanup regressions run with
`python3 tests/check_github_api.py`; they use fixture credentials and no network.

The complete ZIP is installed, preserving assets and workers. A stable
`index.html` symlink points to the versioned HTML file. The matching upstream
license is included as `LICENSE`, and `release.json` records the version, asset,
download URL, and SHA-256. Installed timestamps use the release publication time
so reinstalling the same release does not introduce timestamp-only changes.
No downloaded ZIP is kept in the image or repository.

[install-cyberchef.py](build_files/install-cyberchef.py) implements the download
and extraction. GitHub/network errors, missing checksum metadata, checksum
mismatches, unsafe archive paths, and unexpected HTML/icon layouts fail the build.
CyberChef updates arrive through distro image updates, rather than independently
updating this read-only installation. Since latest is resolved during the build,
repeat builds may select newer releases.

After deploying, disconnect networking, open the menu launcher, and check Base64
encoding/decoding, a worker-based operation such as SHA-256, and file input.
Verify the icon and the browser used. See
[STATUS.md](docs/STATUS.md#validation-evidence) for validation gaps
and [DECISIONS.md](docs/DECISIONS.md#cyberchef-offline-build--2026-10-15) for rationale.

## Bundled Homebrew and Flatpak tools

The full custom bundle is enabled. Aurora's system Flatpak selection remains
excluded through `--exclude-aurora-defaults`; only explicitly selected apps and
their dependencies are prepared. The inherited Homebrew bootstrap is retained.
The manual `ujust install-controlthings-tools` command follows the same Brewfile
and does not remove applications already installed.

The disk workflow offers independent QCOW2, ISO, and VMDK checkboxes; only
QCOW2 is selected by default. VMDK targets VMware Workstation on AMD64. New bundles record `tools.profile=controlthings` and use standard
filenames without a `-smoke` suffix. Reusing an older smoke payload retains its
original profile and suffix.

Publish a container containing the changed manifest and helper before dispatching
the disk workflow with its dated image tag: the disk job reads these files from
the selected container, not the workflow checkout. Prepare a fresh payload for
this expanded bundle; an older retained payload still contains its original apps.
Full-size capacity and offline application launches need validation, starting
with AMD64 QCOW2. The successful payload can then be reused for ISO assembly.
Per-user Python tool provisioning remains deferred.

The [ControlThings Brewfile](system_files/usr/share/ublue-os/homebrew/controlthings.Brewfile)
defines the apps prepared **only during manual disk-image builds**. Normal
container builds ship the list and manual installer; they do not download or
bundle these applications. Aurora's inherited Homebrew bootstrap stays unchanged.

All disk formats install only the Flatpaks selected in ControlThings' Brewfile,
including Bazaar. Aurora's `system-flatpaks.Brewfile` remains excluded, as do
its optional CLI, fonts and DX bundles. Firefox is installed as an RPM in the
OS image and opens the bundled CyberChef application.

The Brewfile is the source of truth for selected apps. It includes CLI tools
such as `eza`, `gping`, `git-delta` (the `delta` command), `libbladerf`, and
`librtlsdr`, plus GUI tools such as Gqrx, Obsidian, ImHex, Okteta, and Bazaar.
ZAP is AMD64-only because Flathub has no ARM64 build. Use simple `brew "name"` and `flatpak "application.ID"`
declarations. The optional `# arch=x86_64` Flatpak annotation restricts an app
to AMD64.

The build checks the native Flathub catalog. Missing selected apps or catalog
errors fail the build. The ZAP architecture annotation excludes it on ARM64.
When ZAP is selected, payload preparation applies
`flatpak override --system --socket=x11 org.zaproxy.ZAP`. The payload retains
the override under `/var/lib/flatpak`; normal OS updates do not retrofit it.
The manual installer applies the same permission with `--user` instead.

The manual disk workflow starts from the selected published container digest
and its shipped manifest. One preparation job per run/architecture prepares Homebrew under
`/var/home/linuxbrew/.linuxbrew` and system Flatpaks under `/var/lib/flatpak`,
including dependencies and extra-data processing. ISO, QCOW2, and VMDK install
these populated stores; their apps need no first-boot download or custom seed
service. Builds require internet access and extra working space. Preparation
retains its image in the separate GHCR `controlthingsplatform-disk-payload`
package, under a unique `run-RUNID-ATTEMPT-ARCH` tag. All selected formats pull its exact
digest; installed systems follow the original OS channel. Cache images are
installer inputs, not supported targets for `bootc switch`.
Before disk assembly, the script removes only its own labelled, dangling
tools-builder images to reclaim duplicate app stores. It reports storage usage
around that cleanup; full builds still require substantial working space.

Publish a container containing the manifest/helper before using this disk path;
older container tags without them fail with an explanatory error. The legacy
local `just build-iso`/`just build-qcow2` recipes do not populate these tools;
use the manual GitHub disk workflow or `scripts/build-disk.py` for bundled images.

Normal container updates preserve installed Homebrew and Flatpak stores and do
not add newly listed apps. To add the current image's tools to an existing
system, run as the Homebrew owner (normally the first login account):

```bash
ujust install-controlthings-tools
```

This installs missing Homebrew formulae without upgrading existing ones, then
installs missing system Flatpaks using Aurora’s native Flatpak authorization,
without wrapping the helper in `pkexec`. ZAP’s X11 override applies to the invoking
user; disk preparation retains its system-wide override. It can
download missing packages and does not remove other tools. Continue using
Homebrew, Flatpak, or Aurora's update tooling for application updates. Installing
Starship and Zoxide does not automatically change shell configuration.

Disk artifact source metadata records the original OS digest, the temporary
payload's local image ID, both manifest checksums, selected package IDs, omitted
ARM64 defaults, Homebrew versions and Flatpak commits. The same initial metadata is installed at
`/var/lib/controlthings/tools/installed.json`; it describes disk provisioning,
not later application updates. QCOW2 and VMDK use a 64 GiB root minimum for the populated
stores; measure remaining space after first boot.

The manual `ujust install-controlthings-tools` command installs ControlThings'
list only; it does not automatically install Aurora's default or optional bundles.

Gqrx's former preinstall declaration was removed with the user's approval.
The unpublished development image that previously tracked it may remove it once
during preinstall reconciliation; reinstall with the command above afterward.
See [current validation](docs/STATUS.md) and [accepted decisions](docs/DECISIONS.md).

## Containerfile

The [Containerfile](./Containerfile) defines the operations used to customize the selected image.This file is the entrypoint for your image build, and works exactly like a regular podman Containerfile. For reference, please see the [Podman Documentation](https://docs.podman.io/en/latest/Introduction.html).

## build.sh

The [build.sh](./build_files/build.sh) file is called from your Containerfile. It is the best place to install new packages or make any other customization to your system. There are customization examples contained within it for your perusal.

Build-time DNF installation disables repository usage counting (`countme`). At
the end of the script, per-repository counting files inherited from the base
image are removed so small bookkeeping changes do not force large layer
downloads on updates. Installed-system repository settings remain inherited.
Use the same counting override for additional build-time DNF commands and keep
cleanup after all package operations. See the
[decision](docs/DECISIONS.md#build-time-dnf-counting-state--2026-10-15) and
[validation status](docs/STATUS.md#image-update-investigations--2026-10-15).

## build.yml

The [build.yml](./.github/workflows/build.yml) Github Actions workflow creates your custom OCI image and publishes it to the Github Container Registry (GHCR). By default, the image name will match the Github repository name.

Scheduled container builds run weekly on Saturdays at 23:00 UTC. GitHub may
delay scheduled runs. Push, pull-request, and manual triggers also remain active.

# Building Disk Images

To compare the compressed container layer sizes of two published tags without
downloading their layers, run:

```bash
./scripts/compare-image-sizes.sh OLD_TAG NEW_TAG
```

This requires `skopeo`, `jq`, and `awk`. It queries the ControlThings GHCR
repository for the host platform and reports both totals in GiB and the
new-minus-old difference in MiB. These totals are not installed disk usage or
the amount downloaded during an update. Registry access uses Skopeo's existing
credentials when authentication is required.

The [Build disk images workflow](.github/workflows/build-disk.yml) runs manually
and builds ISO installers, QCOW2 disks, and VMDK disks for the selected
**platform**: `amd64` (default) or `arm64`. Builds use native Ubuntu runners.
Open **Actions → Build disk images → Run workflow**, select the platform and
**QCOW2**, **ISO**, and/or **VMDK** checkboxes (QCOW2 alone by default), and supply a
published channel (`latest`, `ics410_l01`, or `ics410-l01` if published with that
spelling), or a dated tag such as `latest-20261015-5118339`. Channel names retain
their exact spelling; hyphens and underscores are not aliases.

All selected format jobs use one prepared application payload for the selected architecture. The filename date
and hash come from the source container version label, never the workflow's
checkout or the disk generation date. For example:

- `controlthingsplatform-latest-20261015-5118339-amd64-installer.iso`
- `controlthingsplatform-latest-20261015-5118339-amd64.qcow2`
- `controlthingsplatform-latest-20261015-5118339-amd64.vmdk`

At least one format must be selected. VMDK is restricted to AMD64; selecting
ARM64 with VMDK fails before payload preparation. It uses `monolithicSparse` and
is distributed in a compressed bundle with VMware configuration; latest-channel
bundles also include VirtualBox configuration, as described below.
The previous workflow `format` input has been replaced; CLI/API dispatch callers
must use boolean `qcow2`, `iso`, and `vmdk` inputs. For example, a VMDK-only run
sets `qcow2=false`, `iso=false`, and `vmdk=true`.

For a fresh payload, leave **payload_ref** blank. The preparation job publishes
the payload before disk assembly, writes its source tag and digest reference to
the workflow summary, and uploads a small `disk-payload-...` descriptor artifact.
Final disk metadata includes that reference and exact artifact bytes. Registry
layer bytes are reported separately; they are not installed size or runner peak
storage usage.

For an assembly retry, use GitHub's **Re-run failed jobs** to reuse successful
preparation. For another format or a later workflow revision, dispatch a new run
with the same dated **image_tag** and paste the summary's full
`ghcr.io/controlthings-io/controlthingsplatform-disk-payload@sha256:...` into
**payload_ref**. This skips package installation and downloads the retained
payload directly on the GitHub runner. Changes to the source digest, architecture,
channel, or preparation recipe require fresh preparation; mismatches fail rather
than silently reinstalling apps. Assembly-only fixes can reuse the payload.

The preparation job has `packages: write`; assembly has read-only package access.
Both log into GHCR using the workflow token, including for a private cache package.
The new package is linked to this repository through its source label. Organization
package policies must allow creation/access; that permission is verified by CI's
first push/pull. There is no automatic cache deletion yet: retain referenced
payload versions while retries are needed and remove obsolete cache versions
through GitHub Packages when finished. Deletion prevents later reuse.

Workflow-only changes can use an existing compatible OS tag without waiting for
a new container build. Manifest/helper changes require a new published OS image.
Dependency-image availability is checked before application preparation; this
preflight does not prove adequate full-size runner capacity.

ARM64 outputs use `arm64` in place of `amd64`. The selected tag must publish a
matching container architecture; disk generation cannot convert an AMD64
container into ARM64. The container workflow currently builds AMD64 only, and
the inspected `latest` tag has no ARM64 payload. Publish an ARM64 source before
using that platform; the resolver fails early when it is missing.

VMDK downloads are compressed `.7z` bundles. Latest-channel bundles (including
builds from dated `latest` tags) contain only the versioned VMDK,
`controlthingsplatform.vmx`, and `controlthingsplatform.vbox`. Branch bundles
contain only the VMDK and VMX. GitHub uploads the prebuilt `.7z` directly;
a separate `vmdk-metadata` ZIP artifact holds the disk and bundle `.sha256` files,
`.source.json`, and executed OSBuild manifest. Optional S3 uploads place that same
`.7z` and the metadata/checksum files alongside each other; the unpacked VMDK is
not uploaded separately.

QCOW2 is also a direct GitHub download, without a ZIP wrapper or an additional
compression step. Its `.sha256`, `.source.json` and build manifest are in a
separate `qcow2-metadata` ZIP artifact. CI-generated QCOW2 filenames append the
workflow run and attempt before `.qcow2` so direct uploads remain distinct across
runs and retries; local builds keep the date/hash filename above. S3 continues
to receive the QCOW2 and individual metadata/checksum files. ISO packaging is
unchanged: GitHub provides the image and metadata together in an uncompressed
ZIP, while S3 receives the individual files.

Extract VMDK bundles with a 7z-capable tool, for example `7zz x FILENAME.7z`.
After placing a checksum file beside its corresponding `.7z`, QCOW2 or extracted
disk, verify it with `sha256sum -c FILENAME.sha256`. Metadata records the original
OS digest, disk-only payload image ID, tool versions, requested tag, update
reference, builder, and workflow run. Same-day container rebuilds can reuse
date/hash tags; the recorded identities distinguish their contents. CI VMDK
bundle names contain the workflow run and attempt so repeated runs remain separate.

Installed systems follow their source channel: `latest` updates to `latest`,
`ics410_l01` updates to `ics410_l01`, and `ics410-l01` updates to `ics410-l01`.
Selecting a dated tag fixes the OS source and tool list; app versions resolve at
preparation time. Reusing a payload also freezes its installed app versions. The installed system follows that tag's channel for future
updates. The ISO embeds the prepared disk-only payload and
Anaconda installs from local container storage. ISO offline installation and first login still require VM validation;
QCOW2 smoke results are recorded in STATUS.

## Disk builder and configuration

CI uses the pinned [image-builder CLI](https://github.com/osbuild/image-builder)
container directly. The deprecated bootc-image-builder action cannot express the
new generic installer configuration. The ISO uses `bootc-generic-iso` with a
separate Fedora 44 Anaconda environment defined in
[disk_config/installer/Containerfile](disk_config/installer/Containerfile), based
on the [upstream generic ISO example](https://osbuild.org/docs/developer-guide/projects/image-builder/advanced/bootc/isos/).
Its kickstart explicitly selects the embedded payload and channel update
reference. The installer environment does not become the installed OS.

QCOW2 and VMDK use the new CLI's `--image-size "64 GiB"` root minimum and Btrfs
default, allowing space for the preinstalled Homebrew and Flatpak stores. For
VMDK, assembly generates a manifest with the pinned builder's `manifest vmdk`
command, changes the VMDK QEMU stage to `monolithicSparse` with `compression=false`,
and executes only the `vmdk` export and its dependencies. The VMDK stage writes
the versioned filename directly from the raw disk. There is no intermediate
QCOW2 or streamOptimized disk and no second VMDK conversion. The published
manifest records the actual sparse build options. See the
[OSBuild QEMU stage](https://osbuild.org/docs/developer-guide/projects/osbuild/modules/stages/org.osbuild.qemu/).

The [container runner](scripts/run-osbuild.sh) preserves the pinned image-builder
87.0.0 container setup for SELinux labels and dynamic loop devices. Review it
against upstream `pkg/setup/setup.go` when changing the builder pin. Host
`qemu-img` (`qemu-utils` on Ubuntu) validates capacity, subformat, uncompressed
extents and a self-contained disk before packaging.

The build reads the [VM templates](disk_config/virtualization/) without editing
them. Generated VMX copies use the relative versioned disk basename and display
`ControlThings Platform` for latest or `UPPERCASE_BRANCH - ControlThings Platform`
for branch channels. Generated VBOX copies use the same basename, the VMDK's
`ddb.uuid.image` in both disk references, and a fresh machine UUID per build. If
the disk lacks a VirtualBox media UUID, assembly initializes it in the reserved
descriptor before checksumming. This is distinct from VMware's UUID and filesystem
UUIDs. Both templates default to two vCPUs; VMware presents one socket/two cores.
All other template settings and line endings are preserved.

VMDK packaging requires host `7zz` (`7zip` on Ubuntu 24.04). Bundles use 7z/LZMA2
level 5, a 32 MiB dictionary, and two compression threads. Solid mode is disabled
so extracting a small VM configuration does not require decompressing the disk.
These explicit settings limit resource costs across 7-Zip versions; full-size
compression time, memory and download size still need measurement.

Compression reduces download size; the extracted writable disk remains larger
than streamOptimized. Allow space for OSBuild's raw disk/cache and output, then
the output plus `.7z` during packaging. A temporary hard-link stages the source
disk without another copy. Partial archives and temporary files are removed on
packaging failure. Disk and bundle checksums and source metadata are emitted
after successful packaging; `artifact_bytes` describes the disk, while
`bundle_filename`/`bundle_bytes` describe the download. Local output retains the
unpacked VMDK for inspection.

Run `python3 tests/check_build_disk.py`, `python3 tests/check_disk_payload_reuse.py`,
`python3 tests/check_vmdk.py`, and `python3 tests/check_osbuild_runner.py` for relevant
checks. The VMDK checks need `7zz`; the real small-disk test also needs `qemu-img` and
`qemu-io` and uses the local OSBuild QEMU stage when installed. Mocked container/registry checks do not establish
full image or guest boot success; see [current validation](docs/STATUS.md).

The local legacy disk configuration also uses a 64 GiB root minimum.
The existing `just build-iso`/`just build-qcow2` recipes and
`disk_config/iso.toml`/`disk_config/disk.toml` still use the legacy local builder;
this migration covers the GitHub disk workflow only.

GitHub artifacts are always uploaded. Optionally select **Also upload to S3**;
configure these repository Actions secrets:

- `S3_PROVIDER`: an [rclone S3 provider](https://rclone.org/s3/).
- `S3_BUCKET_NAME`: destination bucket.
- `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY`: credentials for that bucket.
- `S3_REGION`: provider region, or `auto` where supported.
- `S3_ENDPOINT`: provider endpoint.

S3 files go under `SOURCE_TAG/RUN_ID-ATTEMPT/ARCHITECTURE/FORMAT/` to keep runs and formats
separate. Build failures stop image upload. See
[STATUS.md](docs/STATUS.md#next-steps) for validation gaps
and [DECISIONS.md](docs/DECISIONS.md#disk-workflow-and-update-channels--2026-10-15)
for accepted workflow choices.

# Artifacthub

This template comes with the necessary tooling to index your image on [artifacthub.io](https://artifacthub.io). Use the `artifacthub-repo.yml` file at the root to verify yourself as the publisher. This is important to you for a few reasons:

- The value of artifacthub is it's one place for people to index their custom images, and since we depend on each other to learn, it helps grow the community. 
- You get to see your pet project listed with the other cool projects in Cloud Native.
- Since the site puts your README front and center, it's a good way to learn how to write a good README, learn some marketing, finding your audience, etc. 

[Discussion Thread](https://universal-blue.discourse.group/t/listing-your-custom-image-on-artifacthub/6446)

# Justfile Documentation

The `Justfile` contains various commands and configurations for building and managing container images and virtual machine images using Podman and other utilities.
To use it, you must have installed [just](https://just.systems/man/en/introduction.html) from your package manager or manually. It is available by default on all Universal Blue images.

## Environment Variables

These are all sourced from the `image-template.env` file.

- `image_name`: The image name from `image-template.env` (`ControlThingsPlatform`).
- `default_tag`: The default tag for the image (default: "latest").
- `bib_image`: The Bootc Image Builder (BIB) image (default: "quay.io/centos-bootc/bootc-image-builder:latest").

## Building The Image

All these recipes will work (with default values) without supplying any arguments to them, e.g. `just build`

### `just build`

Builds a container image using Podman.

```bash
just build $target_image $tag
```

Arguments:
- `$target_image`: The tag you want to apply to the image (default: `$image_name`).
- `$tag`: The tag for the image (default: `$default_tag`).

### Rechunking

#### `just rechunk`

The container workflow uses [Chunkah](https://github.com/coreos/chunkah), matching
Aurora's approach. It reorganizes the finished filesystem into up to 256 layers
so unchanged layers can be reused during updates. It preserves the selected
image's configuration, removes embedded OSTree data and stale OSTree labels,
imports the temporary OCI output, and retags the result under the same name/tag.
The recipe then runs `bootc container lint` on the result.

```bash
just rechunk $target_image $tag
```

Build and rechunk using the same user's Podman storage. The builder image is
digest-pinned in `Justfile`, with updates managed by Renovate. Temporary files
are cleaned on success or failure. Changing layer layouts can require a larger
first update; subsequent download savings need measurement. Rechunking does not
eliminate changes inside RPM/DNF databases.

#### `just ostree-rechunk`

The previous [rpm-ostree rechunker](https://coreos.github.io/rpm-ostree/build-chunked-oci/)
remains available for explicit comparison or rollback builds; CI uses Chunkah.

```bash
sudo just ostree-rechunk $target_image $tag
```

See [DECISIONS.md](docs/DECISIONS.md#chunkah-rechunking--2026-10-15) for rationale
and [STATUS.md](docs/STATUS.md#validation-evidence) for validation gaps.

### Switching to the locally built image for testing

The image has to be in the containers-storage owned by root, to be able to rebase to it, see the `_rootful_load_image` recipe.

`sudo just build` and `sudo just rechunk` use root's container storage directly,
allowing you to skip the transfer from user storage.

You can rebase to all the images that are in your containers-storage:

```
sudo podman image list --filter=label=containers.bootc=1
```

See [man bootc switch](https://bootc.dev/bootc/man/bootc-switch.8.html) for more info.

```
sudo bootc switch --transport containers-storage localhost/myimage:latest
```

and reboot your system!

## Building and Running Virtual Machines and ISOs

The below commands all build QCOW2 images. To produce or use a different type of image, substitute in the command with that type in the place of `qcow2`. The available types are `qcow2`, `iso`, and `raw`.

### `just build-qcow2`

Builds a QCOW2 virtual machine image.

```bash
just build-qcow2 $target_image $tag
```

### `just rebuild-qcow2`

Rebuilds a QCOW2 virtual machine image.

```bash
just rebuild-vm $target_image $tag
```

### `just run-vm-qcow2`

Runs a virtual machine from a QCOW2 image.

```bash
just run-vm-qcow2 $target_image $tag
```

### `just spawn-vm`

Runs a virtual machine using systemd-vmspawn.

```bash
just spawn-vm rebuild="0" type="qcow2" ram="6G"
```

## File Management

### `just check`

Checks the syntax of all `.just` files and the `Justfile`.

### `just fix`

Fixes the syntax of all `.just` files and the `Justfile`.

### `just clean`

Cleans the repository by removing build artifacts.

### `just lint`

Runs shell check on all Bash scripts.

### `just format`

Runs shfmt on all Bash scripts.

## Additional resources

For additional driver support, ublue maintains a set of scripts and container images available at [ublue-akmod](https://github.com/ublue-os/akmods). These images include the necessary scripts to install multiple kernel drivers within the container (Nvidia, OpenRazer, Framework...). The documentation provides guidance on how to properly integrate these drivers into your container image.

## Community Examples

These are images derived from this template (or similar enough to this template). Reference them when building your image!

- [m2Giles' OS](https://github.com/m2giles/m2os)
- [bOS](https://github.com/bsherman/bos)
- [Homer](https://github.com/bketelsen/homer/)
- [Amy OS](https://github.com/astrovm/amyos)
- [VeneOS](https://github.com/Venefilyn/veneos)

## Firefox homepage and shortcuts

[build_files/firefox-policies.json](build_files/firefox-policies.json) supplies
unlocked homepage settings and `Preferences` entries with `Status: default`.
[build.sh](build_files/build.sh) installs it in the RPM's native-library Firefox
`distribution` directory after package installation; a preexisting policies file
stops the build for reconciliation. There is no profile copied from `/etc/skel`
and no persistent `user.js` that reapplies personal settings.

The homepage is ControlThings on main. `browser.newtabpage.pinned` is a JSON-encoded
array of `{url, label}` objects in display order. One row is selected, while
widgets, stories, and sponsored content default off. Search-engine auto-pinning
is disabled by default so it does not occupy the configured shortcut positions.
The shortcuts apply to Firefox Home/New Tab, independently of the startup URL.
Firefox may fill unused slots from its normal suggestions or browsing history.
Users can change these defaults; their saved settings take precedence. This is
stable default configuration, not a one-time profile migration or a shortcut-list
merge mechanism. A course branch can later change only `Homepage.URL` to localhost.

Run `python3 tests/check_firefox_defaults.py` with the RPM Firefox, Bubblewrap,
RPM tools and local socket access. It uses isolated profiles and a temporary
policy mount to check defaults, pin order/labels, lack of preference locks, and
saved homepage/startup/widget/pin overrides after restarting Firefox. The host
browser installation and existing profiles are not modified. In a built guest,
check `about:policies`, Settings, and New Tab with a fresh user.
