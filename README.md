# Ex-Mortis, a plugin for gedit

Reopen closed windows and optionally restore opened windows from the
previous session  
<https://github.com/jefferyto/gedit-ex-mortis>  
0.1.0

All bug reports, feature requests and miscellaneous comments are welcome
at the [project issue tracker][].

## Requirements

This plugin requires gedit 3.

## Installation

1.  Download the source code (as [zip][] or [tar.gz][]) and extract.
2.  Copy the `controlyourtabs` folder and the appropriate `.plugin` file
    into `~/.local/share/gedit/plugins` (create if it does not exist):
    *   For gedit 3.6 and earlier, copy `controlyourtabs.plugin.python2`
        and rename to `controlyourtabs.plugin`.
    *   For gedit 3.8 and later, copy `controlyourtabs.plugin`.
3.  Restart gedit, then enable the plugin in the **Plugins** tab in
    gedit's **Preferences** window.

## Usage

*   <kbd>Ctrl</kbd>+<kbd>Tab</kbd> /
    <kbd>Ctrl</kbd>+<kbd>Shift</kbd >+<kbd>Tab</kbd> - Switch tabs in
    most recently used order.
*   <kbd>Ctrl</kbd>+<kbd>Page Up</kbd> /
    <kbd>Ctrl</kbd>+<kbd>Page Down</kbd> - Switch tabs in tabbar order.

## Preferences

In gedit 3.4 or later, the plugin supports these preferences:

*   `Use tabbar order for Ctrl+Tab / Ctrl+Shift+Tab` - Change
    <kbd>Ctrl</kbd>+<kbd>Tab</kbd> /
    <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Tab</kbd> to switch tabs in
    tabbar order instead of most recently used order.

## Development

The code in `ex-mortis/utils` comes from [python-gtk-utils][]; changes
should ideally be contributed to that project, then pulled back into
this one with `git subtree pull`.

## Credits

Inspired by:

*   [TabSwitch][] by Elia Sarti
*   [TabPgUpPgDown][] by Eran M.
*   the gedit Documents panel

## License

Copyright &copy; 2017 Jeffery To <jeffery.to@gmail.com>

Available under GNU General Public License version 3


[project issue tracker]: https://github.com/jefferyto/gedit-ex-mortis/issues
[zip]: https://github.com/jefferyto/gedit-ex-mortis/archive/master.zip
[tar.gz]: https://github.com/jefferyto/gedit-ex-mortis/archive/master.tar.gz
[python-gtk-utils]: https://github.com/jefferyto/python-gtk-utils
[TabSwitch]: https://wiki.gnome.org/Apps/Gedit/PluginsOld?action=AttachFile&do=view&target=tabswitch.tar.gz
[TabPgUpPgDown]: https://wiki.gnome.org/Apps/Gedit/PluginsOld?action=AttachFile&do=view&target=tabpgupdown.tar.gz
