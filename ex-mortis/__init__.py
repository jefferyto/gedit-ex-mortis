# -*- coding: utf-8 -*-
#
# __init__.py
# This file is part of Ex-Mortis, a plugin for gedit
#
# Copyright (C) 2017 Jeffery To <jeffery.to@gmail.com>
# https://github.com/jefferyto/gedit-ex-mortis
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gedit', '3.0')

import os.path
from gi.repository import GObject, GLib, Gtk, Gio, Gedit, PeasGtk
from .utils import connect_handlers, disconnect_handlers

GETTEXT_PACKAGE = 'gedit-ex-mortis'
BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
	gettext.bindtextdomain(GETTEXT_PACKAGE, LOCALE_PATH)
	_ = lambda s: gettext.dgettext(GETTEXT_PACKAGE, s);
except:
	_ = lambda s: s


class ExMortisAppActivatable(GObject.Object, Gedit.AppActivatable, PeasGtk.Configurable):
	__gtype_name__ = 'ExMortisAppActivatable'

	app = GObject.property(type=Gedit.App)

	SETTINGS_SCHEMA_ID = 'com.thingsthemselves.gedit.plugins.ex-mortis'

	RESTORE_BETWEEN_SESSIONS = 'restore-between-sessions'

	RESTORE_URIS = 'restore-uris'
	RESTORE_URIS_GVARIANT_TYPE = 'aaas'


	# gedit plugin api

	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		Gedit.debug_plugin_message("")

		app = self.app

		# reopen action
		reopen_action = Gio.SimpleAction(name='reopen-closed-window')
		reopen_action.set_enabled(False)
		connect_handlers(self, reopen_action, ['activate'], 'reopen')
		app.add_action(reopen_action)

		# reopen menu item
		app.set_accels_for_action('app.reopen-closed-window', ['<Primary><Shift>N'])
		menu_ext = self.extend_menu('app-commands-section')
		menu_item = Gio.MenuItem.new(_("Reopen Closed _Window"), 'app.reopen-closed-window')
		menu_ext.append_menu_item(menu_item)

		# quit action
		original_quit_action = app.lookup_action('quit')
		custom_quit_action = Gio.SimpleAction(name='quit')
		connect_handlers(self, custom_quit_action, ['activate'], 'quit')
		app.remove_action('quit')
		app.add_action(custom_quit_action)

		# settings
		settings = self._get_settings()
		if settings:
			connect_handlers(self, settings, ['changed::' + self.RESTORE_BETWEEN_SESSIONS], 'settings')

		# app
		connect_handlers(self, app, ['window-added', 'window-removed', 'shutdown'], 'app')

		self._open_uris = {}
		self._closing_info = {}
		self._closed_uris = []
		self._quitting_info = None
		self._restore_window = None
		self._restore_handler = None
		self._reopen_action = reopen_action
		self._menu_ext = menu_ext
		self._original_quit_action = original_quit_action
		self._custom_quit_action = custom_quit_action
		self._settings = settings

		# windows
		windows = app.get_main_windows()
		if windows:
			# plugin activated during existing session
			for window in windows:
				self._setup_window(window)
		elif self._should_restore_windows():
			# plugin activated during app startup
			self._restore_windows()

	def do_deactivate(self):
		Gedit.debug_plugin_message("")

		app = self.app

		# app
		disconnect_handlers(self, app)

		# windows
		for window in app.get_main_windows():
			self._teardown_window(window)

		# settings
		if self._settings:
			disconnect_handlers(self, self._settings)

		# quit action
		app.remove_action('quit')
		app.add_action(self._original_quit_action)
		disconnect_handlers(self, self._custom_quit_action)

		# reopen menu item
		app.set_accels_for_action('app.reopen-closed-window', [])

		# reopen action
		app.remove_action('reopen-closed-window')

		self._open_uris = None
		self._closing_info = None
		self._closed_uris = None
		self._quitting_info = None
		self._restore_window = None
		self._restore_handler = None
		self._reopen_action = None
		self._menu_ext = None
		self._original_quit_action = None
		self._custom_quit_action = None
		self._settings = None


	# settings ui

	def do_create_configure_widget(self):
		Gedit.debug_plugin_message("")

		settings = self._get_settings()

		if settings:
			widget = Gtk.CheckButton(_("Restore windows between sessions"))
			connect_handlers(self, widget, ['toggled'], 'configure_check_button', settings)
			connect_handlers(self, settings, ['changed::' + self.RESTORE_BETWEEN_SESSIONS], 'configure_settings', widget)
			widget.set_active(settings.get_boolean(self.RESTORE_BETWEEN_SESSIONS))

		else:
			widget = Gtk.Box()
			widget.add(Gtk.Label(_("Could not load settings schema")))

		widget.set_border_width(5)

		return widget

	def on_configure_check_button_toggled(self, widget, settings):
		should_restore = widget.get_active()

		Gedit.debug_plugin_message("%s", should_restore)

		settings.set_boolean(self.RESTORE_BETWEEN_SESSIONS, should_restore)

	def on_configure_settings_changed_restore_between_sessions(self, settings, prop, widget):
		should_restore = settings.get_boolean(self.RESTORE_BETWEEN_SESSIONS)

		Gedit.debug_plugin_message("%s", should_restore)

		widget.set_active(should_restore)


	# window setup

	def _setup_window(self, window):
		Gedit.debug_plugin_message("%s", window)

		connect_handlers(self, window, ['delete-event', 'tab-added', 'tab-removed', 'tabs-reordered'], 'window')

		for document in window.get_documents():
			self._setup_tab(window, Gedit.Tab.get_from_document(document))

		self._update_open_uris(window)

	def _teardown_window(self, window):
		Gedit.debug_plugin_message("%s", window)

		disconnect_handlers(self, window)

		if window is self._restore_window:
			window.disconnect(self._restore_handler)
			self._restore_window = None
			self._restore_handler = None

		for document in window.get_documents():
			self._teardown_tab(window, Gedit.Tab.get_from_document(document))

		self._update_open_uris(window)


	# tab setup

	def _setup_tab(self, window, tab):
		Gedit.debug_plugin_message("%s %s", window, tab)

		connect_handlers(self, tab.get_document().get_file(), ['notify::location'], 'source_file', window)

		self._update_open_uris(window)

	def _teardown_tab(self, window, tab):
		Gedit.debug_plugin_message("%s %s", window, tab)

		disconnect_handlers(self, tab.get_document().get_file())

		self._update_open_uris(window)


	# signal handlers

	def on_app_window_added(self, app, window):
		# preferences window also triggers this signal
		if isinstance(window, Gedit.Window):
			Gedit.debug_plugin_message("%s", window)

			self._cancel_quitting()

			self._setup_window(window)

	def on_app_window_removed(self, app, window):
		# preferences window also triggers this signal
		if isinstance(window, Gedit.Window):
			Gedit.debug_plugin_message("%s", window)

			self._end_closing_window(window)

			self._teardown_window(window)

	def on_app_shutdown(self, app):
		Gedit.debug_plugin_message("")

		self._end_quitting()

	def on_window_delete_event(self, window, event):
		Gedit.debug_plugin_message("%s", window)

		# closing the only window also quits the app
		if len(self.app.get_main_windows()) == 1:
			self._start_quitting()

		self._start_closing_window(window)

		return False

	def on_window_tab_added(self, window, tab):
		Gedit.debug_plugin_message("%s %s", window, tab)

		self._cancel_closing_window(window)

		self._cancel_quitting()

		self._setup_tab(window, tab)

	def on_window_tab_removed(self, window, tab):
		Gedit.debug_plugin_message("%s %s", window, tab)

		self._update_closing_window(window, tab)

		self._update_quitting(window, tab)

		self._teardown_tab(window, tab)

	def on_window_tabs_reordered(self, window):
		Gedit.debug_plugin_message("%s", window)

		self._cancel_closing_window(window)

		self._cancel_quitting()

		self._update_open_uris(window)

	def on_source_file_notify_location(self, source_file, pspec, window):
		location = source_file.get_location()
		uri = location.get_uri() if location else None

		Gedit.debug_plugin_message("%s", uri)

		self._update_open_uris(window)

	def on_settings_changed_restore_between_sessions(self, settings, prop):
		should_restore = settings.get_boolean(self.RESTORE_BETWEEN_SESSIONS)

		Gedit.debug_plugin_message("%s", should_restore)

		self._save_open_uris()

	def on_reopen_activate(self, action, parameter):
		Gedit.debug_plugin_message("")

		self._reopen_closed_window()

	def on_quit_activate(self, action, parameter):
		Gedit.debug_plugin_message("")

		self._start_quitting()

		for window in self.app.get_main_windows():
			self._start_closing_window(window)

		self._original_quit_action.activate()


	# closing window

	def _is_closing_window(self, window):
		return window in self._closing_info

	def _start_closing_window(self, window):
		Gedit.debug_plugin_message("%s", window)

		self._closing_info[window] = self._get_window_info(window)

		Gedit.debug_plugin_message("%s", self._closing_info[window])

	def _cancel_closing_window(self, window):
		Gedit.debug_plugin_message("%s", window)

		if self._is_closing_window(window):
			Gedit.debug_plugin_message("closing window started, cancelling")

			del self._closing_info[window]

	def _update_closing_window(self, window, tab):
		Gedit.debug_plugin_message("%s %s", window, tab)

		if self._is_closing_window(window):
			self._update_window_uris(*self._closing_info[window], tab)

	def _end_closing_window(self, window):
		Gedit.debug_plugin_message("%s", window)

		if self._is_closing_window(window):
			uris = self._filter_window_uris(*self._closing_info[window])

			if uris:
				Gedit.debug_plugin_message("window has reopenable files, caching")

				self._closed_uris.append(uris)
				self._reopen_action.set_enabled(True)

			else:
				Gedit.debug_plugin_message("window does not have reopenable files, ignoring")

			del self._closing_info[window]

		else:
			Gedit.debug_plugin_message("end closing window without starting?")


	# reopen window

	def _reopen_closed_window(self):
		Gedit.debug_plugin_message("")

		closed_uris = self._closed_uris

		if len(closed_uris) > 0:
			Gedit.debug_plugin_message("have cached windows, reopening")

			self._open_uris_in_window(closed_uris.pop())
			self._reopen_action.set_enabled(len(closed_uris) > 0)

		else:
			Gedit.debug_plugin_message("do not have cached windows, how did we get here?")


	# quitting

	def _is_quitting(self):
		return self._quitting_info is not None

	def _start_quitting(self):
		Gedit.debug_plugin_message("")

		self._quitting_info = {window : self._get_window_info(window) for window in self.app.get_main_windows()}

	def _cancel_quitting(self):
		Gedit.debug_plugin_message("")

		if self._is_quitting():
			Gedit.debug_plugin_message("quitting started, cancelling")

			self._quitting_info = None

	def _update_quitting(self, window, tab):
		Gedit.debug_plugin_message("%s %s", window, tab)

		if self._is_quitting():
			if window in self._quitting_info:
				self._update_window_uris(*self._quitting_info[window], tab)

			else:
				Gedit.debug_plugin_message("quitting started but window is not tracked?")

	def _end_quitting(self):
		Gedit.debug_plugin_message("")

		if self._is_quitting():
			quitting_uris = {window : self._filter_window_uris(*info) for window, info in self._quitting_info.items()}

			Gedit.debug_plugin_message("saving %d windows", len(quitting_uris))

			self._set_restore_uris(quitting_uris)

			self._quitting_info = None

		else:
			Gedit.debug_plugin_message("end quitting without starting?")


	# restore windows

	def _should_restore_windows(self):
		settings = self._settings
		return settings and settings.get_boolean(self.RESTORE_BETWEEN_SESSIONS)

	def _restore_windows(self):
		Gedit.debug_plugin_message("")

		uris_list = self._get_restore_uris()

		Gedit.debug_plugin_message("restoring %d windows", len(uris_list))

		for uris in uris_list:
			self._open_uris_in_window(uris)

		window = self.app.get_active_window()

		if window:
			Gedit.debug_plugin_message("waiting for new tab in %s", window)
			self._restore_window = window
			self._restore_handler = window.connect('tab-added', self.on_restore_window_tab_added)

	def on_restore_window_tab_added(self, window, tab):
		Gedit.debug_plugin_message("%s %s", window, tab)

		if tab.get_document().is_untouched() and tab.get_state() is Gedit.TabState.STATE_NORMAL:
			Gedit.debug_plugin_message("closing untouched tab")

			def close_tab():
				window.close_tab(tab)
				return False

			GObject.idle_add(close_tab)

		else:
			Gedit.debug_plugin_message("new tab is not untouched")

		window.disconnect(self._restore_handler)
		self._restore_window = None
		self._restore_handler = None


	# saving open uris

	def _update_open_uris(self, window):
		changed = False

		if window in self.app.get_main_windows():
			self._open_uris[window] = self._filter_window_uris(*self._get_window_info(window))
			changed = True

		elif window in self._open_uris:
			del self._open_uris[window]
			changed = True

		if changed:
			self._save_open_uris()

	def _save_open_uris(self):
		self._set_restore_uris(self._open_uris)


	# settings

	def _get_settings(self):
		schemas_path = os.path.join(BASE_PATH, 'schemas')

		try:
			schema_source = Gio.SettingsSchemaSource.new_from_directory(schemas_path, Gio.SettingsSchemaSource.get_default(), False)
			schema = Gio.SettingsSchemaSource.lookup(schema_source, self.SETTINGS_SCHEMA_ID, False)
			settings = Gio.Settings.new_full(schema, None, None) if schema else None

		except:
			Gedit.debug_plugin_message("could not load settings schema from %s", schemas_path)
			settings = None

		return settings

	def _get_restore_uris(self):
		settings = self._settings
		return settings.get_value(self.RESTORE_URIS) if settings else None

	def _set_restore_uris(self, uris_dict):
		settings = self._settings

		if settings:
			value = [uris for uris in uris_dict.values() if uris] if self._should_restore_windows() else []
			settings.set_value(self.RESTORE_URIS, GLib.Variant(self.RESTORE_URIS_GVARIANT_TYPE, value))


	# uris

	def _get_window_info(self, window):
		window_uris = []
		notebook_map = {}
		# don't map document objects because document objects are transient
		# whereas tab objects are more permanent?
		tab_map = {}

		for document in window.get_documents():
			tab = Gedit.Tab.get_from_document(document)
			notebook = tab.get_parent()

			if notebook not in notebook_map:
				notebook_map[notebook] = len(window_uris)
				window_uris.append([])

			notebook_index = notebook_map[notebook]
			notebook_uris = window_uris[notebook_index]

			tab_index = len(notebook_uris)
			notebook_uris.append(self._get_document_uri(document))

			tab_map[id(tab)] = (notebook_index, tab_index)

		return (window_uris, tab_map)

	def _update_window_uris(self, window_uris, tab_map, tab):
		tab_id = id(tab)
		if tab_id in tab_map:
			notebook_index, tab_index = tab_map[tab_id]
			window_uris[notebook_index][tab_index] = self._get_document_uri(tab.get_document())
		else:
			Gedit.debug_plugin_message("tab id not in tab map?")

	def _filter_window_uris(self, window_uris, tab_map=None):
		window_uris = [[uri for uri in notebook_uris if uri] for notebook_uris in window_uris]
		return [notebook_uris for notebook_uris in window_uris if notebook_uris]

	def _get_document_uri(self, document):
		source_file = document.get_file()
		location = source_file.get_location() if source_file else None
		uri = location.get_uri() if location else None
		return uri

	def _open_uris_in_window(self, window_uris, window=None):
		flattened = [uri for notebook_uris in window_uris for uri in notebook_uris if uri]

		if flattened:
			if not window:
				window = Gedit.App.create_window(self.app, None)

			window.show()

			is_first_notebook = True

			for notebook_uris in window_uris:
				if notebook_uris:
					if not is_first_notebook:
						window.activate_action('new-tab-group')

					locations = [Gio.File.new_for_uri(uri) for uri in notebook_uris if uri]
					Gedit.commands_load_locations(window, locations, None, 0, 0)
					is_first_notebook = False

			window.present()
