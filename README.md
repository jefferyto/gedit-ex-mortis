# Ex-Mortis, a plugin for gedit

Reopen closed windows and optionally restore opened windows from the
previous session  
<https://github.com/jefferyto/gedit-ex-mortis>  
0.1.0

All bug reports, feature requests and miscellaneous comments are welcome
at the [project issue tracker][].

## Requirements

This plugin requires gedit 3.12 or newer.

## Installation

1.  Download the source code (as [zip][] or [tar.gz][]) and extract.
2.  Copy the `ex-mortis` folder and the `ex-mortis.plugin` file into
    `~/.local/share/gedit/plugins` (create if it does not exist).
3.  Restart gedit, then enable the plugin in the **Plugins** tab in
    gedit's **Preferences** window.
4.  Restart gedit again, preferably using **Quit** in the Application
    menu or the File menu. This is necessary because the plugin cannot
    reopen any windows that are open when the plugin was activated.

## Usage

*   This plugin adds a new **Reopen Closed Window** menu item, following
    **New Window** in either the Application menu or the File menu.

    This menu item will reopen the most recently closed window in the
    current session; if there are no closed windows in the current
    session, the menu item will be disabled.

    This menu item can also be activated from the keyboard with
    <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>N</kbd>
    (<kbd>Command</kbd>+<kbd>Shift</kbd>+<kbd>N</kbd> on macOS).

*   If enabled in preferences, this plugin will also restore windows
    between gedit sessions.

Note that only saved files will be reopened. Unsaved files or unsaved
changes are not cached in any way. Closed windows with no saved files,
i.e. only unsaved or blank documents, will not be reopenable.

## Preferences

*   `Restore windows between sessions` - If enabled, windows that were
    open in the previous session will be reopened when gedit is started
    again. (Default: Disabled)

## Development

The code in `ex-mortis/utils` comes from [python-gtk-utils][]; changes
should ideally be contributed to that project, then pulled back into
this one with `git subtree pull`.

## Credits

Inspired by:

*   [Restore Tabs][] by Quixotix

## License

Copyright &copy; 2017 Jeffery To <jeffery.to@gmail.com>

Available under GNU General Public License version 3


[project issue tracker]: https://github.com/jefferyto/gedit-ex-mortis/issues
[zip]: https://github.com/jefferyto/gedit-ex-mortis/archive/master.zip
[tar.gz]: https://github.com/jefferyto/gedit-ex-mortis/archive/master.tar.gz
[python-gtk-utils]: https://github.com/jefferyto/python-gtk-utils
[Restore Tabs]: https://github.com/Quixotix/gedit-restore-tabs
