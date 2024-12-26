# Changelog

## [0.2.4-dev][Unreleased] - Unreleased
* Fixed AttributeError when loaded in gedit 48 ([#12])

## [0.2.3] - 2024-06-07
* Fixed error when loaded in gedit 47 ([#11])

## [0.2.2] - 2023-11-02
* Fixed AttributeError when loaded in gedit 46 ([#9])

## [0.2.1] - 2023-05-03
* Fixed AttributeError when loaded in gedit 44

## [0.2.0] - 2019-03-22
* Restore windows on startup, and save windows for restoring, only for
  the primary instance, i.e. when gedit is not in standalone mode
* When restoring windows on startup, reuse the new window/tab ([#4])
* Fixed adding "Reopen Closed Window" menu item on platforms with no app
  menu or menu bar ([#5])
* Added Russian translation ([#6], thanks Habetdin!)

## [0.1.2] - 2018-03-13
* Fixed auto-closing gedit if there are no windows to restore ([#1])
* Fixed (potentially) affecting the translations of other plugins

## [0.1.1] - 2017-10-13
* Added .pot file

## 0.1.0 - 2017-10-13
* Initial release


[Unreleased]: https://github.com/jefferyto/gedit-ex-mortis/compare/0.2.3...main
[0.2.3]: https://github.com/jefferyto/gedit-ex-mortis/compare/0.2.2...0.2.3
[0.2.2]: https://github.com/jefferyto/gedit-ex-mortis/compare/0.2.1...0.2.2
[0.2.1]: https://github.com/jefferyto/gedit-ex-mortis/compare/0.2.0...0.2.1
[0.2.0]: https://github.com/jefferyto/gedit-ex-mortis/compare/0.1.2...0.2.0
[0.1.2]: https://github.com/jefferyto/gedit-ex-mortis/compare/0.1.1...0.1.2
[0.1.1]: https://github.com/jefferyto/gedit-ex-mortis/compare/0.1.0...0.1.1

[#1]: https://github.com/jefferyto/gedit-ex-mortis/issues/1
[#4]: https://github.com/jefferyto/gedit-ex-mortis/issues/4
[#5]: https://github.com/jefferyto/gedit-ex-mortis/issues/5
[#6]: https://github.com/jefferyto/gedit-ex-mortis/pull/6
[#9]: https://github.com/jefferyto/gedit-ex-mortis/issues/9
[#11]: https://github.com/jefferyto/gedit-ex-mortis/issues/11
[#12]: https://github.com/jefferyto/gedit-ex-mortis/issues/12
