// Plasma runs this setup hook when creating a Folder View desktop containment.
// Select the wallpaper package so Plasma can choose an image for the display size.
// Existing desktops keep their saved settings; this is not a login/autostart script.
applet.wallpaperPlugin = 'org.kde.image';
applet.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
applet.writeConfig('Image', '/usr/share/wallpapers/CT-De-Machina-Logica-Programmabilis/');
applet.reloadConfig();
