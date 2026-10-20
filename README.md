# ControlThings Platform

ControlThings Platform is an Aurora-based KDE Linux desktop for security
assessment and penetration testing of operational technology (OT) and industrial
control systems (ICS). It combines an image-based operating system with selected
assessment tools and a customized desktop and terminal environment.

The main image builds on [Aurora DX](https://getaurora.dev/). Course variants can
choose a different Aurora base and package selection while sharing the build tools.

## What's included

- Wireshark and helpers for packet- and USB-capture group membership.
- Firefox and a bundled offline CyberChef application for data analysis.
- Selected Homebrew command-line tools and Flatpak applications, including Gqrx,
  ImHex, Okteta, Obsidian, and Bazaar in prepared disk images.
- ControlThings wallpapers and shell configuration. Aurora's terminal MOTD starts
  disabled for new users and can be enabled later.

The [Brewfile](system_files/usr/share/ublue-os/homebrew/controlthings.Brewfile) lists
selected Brew/Flatpak apps; [build.sh](build_files/build.sh) lists additional RPMs.
App selection varies by source revision and architecture; ZAP is AMD64-only.

## Getting an image

ISO installers and QCOW2 VM disks are produced by the manual
[Build disk images workflow](https://github.com/ControlThings-io/ControlThingsPlatform/actions/workflows/build-disk.yml).
Download the desired artifact from a successful run and verify its checksum:

```bash
sha256sum -c FILENAME.sha256
```

Use QCOW2 for a virtual machine or the ISO to install onto a target disk. The
included `.source.json` identifies the source OS, channel, and application payload.
Main follows `latest`; course images follow their own channel, such as `ics410_l01`.

AMD64 smoke QCOW2 boot, offline operation, and application persistence across an
OS update have been reported working. The user reports all selected Flatpak and Brew apps functional; ISO installation
validation remains pending. See [current validation and gaps](docs/STATUS.md) before
choosing an image for a class or deployment. The disk workflow also offers ARM64,
which requires a separately published ARM64 OS source.

## Using the tools

Open CyberChef from the application menu to use its bundled offline copy in
Firefox. Manage CLI apps through Homebrew and GUI apps through Bazaar or Flatpak.
Normal OS container updates preserve these application stores; they do not
install newly added Brewfile entries automatically.

To install the current image's selected tools on an existing system, run this
as the Homebrew owner (normally the first login user):

```bash
ujust install-controlthings-tools
```

This may download packages. System Flatpaks use Aurora’s normal Flatpak
authorization without an extra administrator prompt from this helper. An OS container switch alone does not supply the disk image's app bundle.

Disk builds include a system-wide X11 workaround for ZAP. The manual installer
applies it for the invoking user. Other existing users can apply it and restart ZAP:

```bash
flatpak override --user --socket=x11 org.zaproxy.ZAP
```

For capture-group access, run as your normal login user, then log out and back in:

```bash
ujust controlthings-groups
```

Capture also depends on hardware and device permissions. Run `ujust update` for
manual updates, `ujust toggle-updates` to configure Aurora automatic updates, or
`ujust toggle-user-motd` to change your terminal MOTD preference. Course defaults
may differ. CyberChef itself updates with the OS image.

## Firefox defaults

Firefox starts at [ControlThings](https://www.controlthings.io). New Tab starts
with one row of pinned links: ControlThings Website, ControlThings Discord,
ICS410, SANS ICS, CS2AI, and Fedora Project, in that order. Widgets, stories, and
Support Firefox sponsored content start disabled.

These are editable defaults. Change startup/homepage options in Firefox Settings,
and edit, remove, or rearrange shortcuts through the New Tab page. Existing
personal preferences take precedence; no browser profile is replaced.

## Documentation and development

- [Aurora documentation](https://docs.getaurora.dev/) — the underlying desktop.
- [Development guide](DEVELOPMENT.md) — building, customizing, signing, and disk images.
- [Current status](docs/STATUS.md) — validation evidence, gaps, and next steps.
- [Decisions](docs/DECISIONS.md) — shared design choices and rationale.
- [Project issues](https://github.com/ControlThings-io/ControlThingsPlatform/issues) — bugs and feature requests.

Long-lived branches keep their specific decisions and status under `docs/<branch>/`.
For example, consult `docs/ics410_l01/` when working on that course branch.

## Upstream and license

Built on [Aurora](https://github.com/ublue-os/aurora) and the
[Universal Blue image template](https://github.com/ublue-os/image-template), using
[bootc](https://github.com/bootc-dev/bootc). This repository is licensed under
[Apache-2.0](LICENSE); bundled upstream components retain their own licenses.
