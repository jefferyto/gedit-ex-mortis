# Ex-Mortis, a plugin for gedit

Reopen closed windows and optionally restore windows between sessions  
<https://github.com/jefferyto/gedit-ex-mortis>  
0.2.3-dev

All bug reports, feature requests and miscellaneous comments are welcome
at the [project issue tracker][].

[project issue tracker]: https://github.com/jefferyto/gedit-ex-mortis/issues

## Requirements

This plugin requires gedit 3.12 or newer.

## Installation

1.  Download the [latest release][] and extract.
2.  Copy the `ex-mortis` folder and the `ex-mortis.plugin` file into
    `~/.local/share/gedit/plugins` (create if it does not exist).
3.  Restart gedit, then activate the plugin in the **Plugins** tab in
    gedit's **Preferences** window.
4.  Restart gedit again, preferably using **Quit** in the Application
    menu or the File menu. This is necessary because the plugin cannot
    reopen any windows that were open when the plugin was activated.

If you have previously activated the Dashboard or Zeitgeist plugins
(part of the gedit-plugins package), you may want to deactivate them as
they may [conflict][] with this plugin.

[latest release]: https://github.com/jefferyto/gedit-ex-mortis/releases/latest
[conflict]: https://github.com/jefferyto/gedit-ex-mortis/issues/2

## Usage

*   This plugin adds a new **Reopen Closed Window** menu item, following
    **New Window** in either the Application menu or the File menu.

    Activating this menu item will reopen the most recently closed
    window in the current session; if there are no closed windows, the
    menu item will be disabled.

    This menu item can also be activated from the keyboard with
    <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>N</kbd>
    (<kbd>Command</kbd>+<kbd>Shift</kbd>+<kbd>N</kbd> on macOS).

*   If enabled in preferences, this plugin will also restore windows
    between gedit sessions.

    Window information is tracked in real-time, i.e. when files are
    opened and closed, so that if gedit crashes or is closed
    unexpectedly, when gedit is restarted all windows will be restored
    to the previous state.

Note that only saved files will be reopened. Unsaved files or unsaved
changes are not cached in any way. Closed windows with no saved files,
i.e. only unsaved or blank documents, will not be reopenable.

## Preferences

*   `Restore windows between sessions` - If enabled, windows that were
    open in the previous session will be reopened when gedit is started
    again. (Default: Disabled)

## Contributing

The code in `ex-mortis/utils` comes from [python-gtk-utils][]; changes
should ideally be contributed to that project, then pulled back into
this one with `git subtree pull`.

[python-gtk-utils]: https://github.com/jefferyto/python-gtk-utils

## Credits

Inspired by:

*   [Restore Tabs][] by Quixotix

[Restore Tabs]: https://github.com/Quixotix/gedit-restore-tabs

## License

Copyright &copy; 2017-2019, 2023 Jeffery To <jeffery.to@gmail.com>

Available under GNU General Public License version 3
