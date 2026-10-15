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

## Default lock-screen background — 2026-10-14

Accepted user choice: the lock-screen background should use
`CT-Aquila-Aurea-Machina`. This supersedes the initial assumption that it should
match the desktop. The desktop default remains
`CT-De-Machina-Logica-Programmabilis`.

Ship `kscreenlockerrc` in Aurora's existing
`/usr/share/kde-settings/kde-profile/default/xdg` system-default directory. Host
inspection confirms that Aurora includes this directory in `XDG_CONFIG_DIRS`.
Override only its image-plugin and wallpaper/preview defaults. Do not write
individual user profiles or mark settings immutable. User configuration takes
precedence; existing users who inherit system defaults can see the change too.
Do not alter locking behavior, authentication requirements, or the login screen.

See [README.md](../README.md#default-lock-screen-background) for usage and
[STATUS.md](STATUS.md) for validation gaps.
