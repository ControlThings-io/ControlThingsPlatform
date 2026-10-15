# Decisions

## Default desktop wallpaper — 2026-10-14

Accepted user choice: new users should receive
`CT-De-Machina-Logica-Programmabilis` as their desktop wallpaper.

Implementation: replace Aurora's Folder View creation hook in both its dark
and light global themes with one shared script, `build_files/plasma-desktop.js`.
The installed Aurora themes explicitly select `/usr/share/backgrounds/default.jxl`
in that hook, so setting only a theme's `[Wallpaper]` default would not reliably
override it. Keep the rest of Aurora's theme and panel configuration intact.
Use a wallpaper package directory so Plasma can select a display-appropriate
image. Do not copy a user's desktop configuration or run a wallpaper reset at
every login. Existing desktop settings remain in the user's profile; newly
created desktops (including extra monitors/activities) use the new default.

The image build deliberately fails if either expected Aurora setup directory
is absent, making upstream theme-layout changes visible during CI. This is a
desktop default, not login-screen, lock-screen, or installer branding.

See [README.md](../README.md#default-desktop-wallpaper) for configuration and
[STATUS.md](STATUS.md) for validation and remaining work.
