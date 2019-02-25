# -*- coding: utf-8 -*-
#
# __init__.py
# This file is part of Ex-Mortis, a plugin for gedit
#
# Copyright (C) 2017-2018 Jeffery To <jeffery.to@gmail.com>
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
from gi.repository import GObject, Gtk, Gio, Gedit, PeasGtk
from .closingmixin import ClosingMixin
from .existingmixin import ExistingMixin
from .quittingmixin import QuittingMixin
from .settings import ExMortisSettings
from .windowmanager import ExMortisWindowManager
from .utils import connect_handlers, disconnect_handlers, create_bindings
from . import log

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
	import gettext
	gettext.bindtextdomain('gedit-ex-mortis', LOCALE_PATH)
	_ = lambda s: gettext.dgettext('gedit-ex-mortis', s)
except:
	_ = lambda s: s


class ExMortisAppActivatable(
		ExistingMixin, ClosingMixin, QuittingMixin,
		GObject.Object, Gedit.AppActivatable):

	__gtype_name__ = 'ExMortisAppActivatable'

	app = GObject.Property(type=Gedit.App)


	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		app = self.app
		is_primary = not (app.get_flags() & Gio.ApplicationFlags.NON_UNIQUE)
		window_manager = ExMortisWindowManager()
		settings = ExMortisSettings(is_primary)

		# app
		connect_handlers(
			self, app,
			['window-added', 'window-removed', 'shutdown'],
			'app'
		)

		# window manager
		connect_handlers(
			self, window_manager,
			['tab-added', 'tab-removed', 'tabs-reordered'],
			'window_manager'
		)

		# settings
		connect_handlers(
			self, settings,
			['notify::restore-between-sessions'],
			'settings',
			window_manager
		)

		# reopen action
		reopen_action = Gio.SimpleAction.new('reopen-closed-window', None)
		reopen_action.set_enabled(False)
		connect_handlers(
			self, reopen_action,
			['activate'],
			'reopen',
			window_manager
		)
		app.add_action(reopen_action)

		# reopen menu item
		app.set_accels_for_action(
			'app.reopen-closed-window', ['<Primary><Shift>N']
		)
		menu_ext = self.extend_menu('app-commands-section')
		if not menu_ext:
			menu_ext = self.extend_menu('file-section')
		menu_item = Gio.MenuItem.new(
			_("Reopen Closed _Window"), 'app.reopen-closed-window'
		)
		menu_ext.append_menu_item(menu_item)

		# quit action
		original_quit_action = app.lookup_action('quit')
		custom_quit_action = Gio.SimpleAction.new('quit', None)
		connect_handlers(
			self, custom_quit_action,
			['activate'],
			'quit',
			window_manager
		)
		app.remove_action('quit')
		app.add_action(custom_quit_action)

		self._window_manager = window_manager
		self._settings = settings
		self._reopen_action = reopen_action
		self._menu_ext = menu_ext
		self._original_quit_action = original_quit_action
		self._custom_quit_action = custom_quit_action

		self.do_activate_existing()
		self.do_activate_closing()
		self.do_activate_quitting(settings.restore_between_sessions)

		# windows
		windows = app.get_main_windows()

		self.handle_restore_data(
			window_manager, settings,
			settings.restore_between_sessions and not windows
		)

		if windows:
			# plugin activated during existing session
			for window in windows:
				self.setup_window(window, True)

	def do_deactivate(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		app = self.app
		window_manager = self._window_manager
		settings = self._settings

		# windows
		for window in app.get_main_windows():
			self.teardown_window(window)

		# quit action
		app.remove_action('quit')
		app.add_action(self._original_quit_action)
		disconnect_handlers(self, self._custom_quit_action)

		# reopen menu item
		app.set_accels_for_action('app.reopen-closed-window', [])

		# reopen action
		app.remove_action('reopen-closed-window')

		# settings
		disconnect_handlers(self, settings)

		# window manager
		disconnect_handlers(self, window_manager)

		# app
		disconnect_handlers(self, app)

		window_manager.cleanup()
		settings.cleanup()

		self._window_manager = None
		self._settings = None
		self._reopen_action = None
		self._menu_ext = None
		self._original_quit_action = None
		self._custom_quit_action = None

		self.do_deactivate_existing()
		self.do_deactivate_closing()
		self.do_deactivate_quitting()


	# window setup

	def setup_window(self, window, is_existing=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, is_existing=%s", window, is_existing))

		window_manager = self._window_manager
		settings = self._settings

		if is_existing:
			info_bar, quit_response_id = self.add_existing(window)

			connect_handlers(
				self, info_bar,
				['response'],
				'existing_window_info_bar',
				quit_response_id
			)

			self.show_existing_info_bar(window)

		connect_handlers(
			self, window,
			['delete-event'],
			'window',
			window_manager
		)

		window_manager.track_window(window)

		self.setup_restore_window(window_manager, window)

		if self.is_saving_window_states():
			self.bind_window_settings(window_manager, settings, window)

	def teardown_window(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		window_manager = self._window_manager
		settings = self._settings

		if self.is_existing(window):
			info_bar = self.get_existing_info_bar(window)
			disconnect_handlers(self, info_bar)

			self.remove_existing(window)

		disconnect_handlers(self, window)

		self.teardown_restore_window(window)

		if self.is_saving_window_states():
			self.unbind_window_settings(window_manager, settings, window)

		window_manager.untrack_window(window)


	# start closing / quitting

	def on_window_delete_event(self, window, event, window_manager):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		# closing the only window also quits the app
		if len(self.app.get_main_windows()) == 1:
			self.start_quitting(window_manager)

		# this handler would not be called on an existing window anyway
		# but for completeness sake...
		if not self.is_existing(window):
			self.start_closing(window_manager, window)

		return False

	def on_quit_activate(self, action, parameter, window_manager):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		try:
			self.start_quitting(window_manager)

			for window in self.app.get_main_windows():
				if not self.is_existing(window):
					self.start_closing(window_manager, window)

		finally:
			self.really_quit()


	# update and cancel closing / quitting

	def on_window_manager_tab_removed(self, window_manager, window, tab):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		if not self.is_existing(window):
			self.update_closing(window, tab)

		self.update_quitting(window, tab)

	def on_window_manager_tab_added(self, window_manager, window, tab):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		if not self.is_existing(window):
			self.cancel_closing(window)

		self.cancel_quitting()

	def on_window_manager_tabs_reordered(self, window_manager, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not self.is_existing(window):
			self.cancel_closing(window)

		self.cancel_quitting()

	def on_app_window_added(self, app, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not isinstance(window, Gedit.Window):
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("not a main window"))

			return

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("a main window"))

		self.cancel_quitting()

		self.setup_window(window)


	# end closing / quitting

	def on_app_window_removed(self, app, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not isinstance(window, Gedit.Window):
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("not a main window"))

			return

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("a main window"))

		if not self.is_existing(window):
			self.end_closing(window)
			self.update_reopen_action_enabled()

		self.teardown_window(window)

	def on_app_shutdown(self, app):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		settings = self._settings

		self.end_quitting(settings, settings.restore_between_sessions)


	# toggled restore between sessions setting

	def on_settings_notify_restore_between_sessions(self, settings, pspec, window_manager):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		restore_between_sessions = settings.restore_between_sessions

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("restore-between-sessions=%s", restore_between_sessions))

		if restore_between_sessions == self.is_saving_window_states():
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("setting has not changed"))

			return

		if restore_between_sessions:
			self.start_saving_window_states(window_manager, settings)
		else:
			self.stop_saving_window_states(window_manager, settings)


	# reopen closed window

	def on_reopen_activate(self, action, parameter, window_manager):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		self.reopen_closed(window_manager)
		self.update_reopen_action_enabled()


	# existing window info bar response

	def on_existing_window_info_bar_response(self, info_bar, response_id, quit_response_id):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("response_id=%s", response_id))

		info_bar.hide()

		if response_id == quit_response_id:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("quit selected"))

			self.app.activate_action('quit')

		else:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("quit not selected"))


	# helpers

	def update_reopen_action_enabled(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		can_reopen = self.can_reopen()

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("can_reopen=%s", can_reopen))

		self._reopen_action.set_enabled(can_reopen)

	def really_quit(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		self._original_quit_action.activate()


class ExMortisConfigurable(GObject.Object, PeasGtk.Configurable):

	__gtype_name__ = 'ExMortisConfigurable'


	def do_create_configure_widget(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		app = Gedit.App.get_default()
		is_primary = not (app.get_flags() & Gio.ApplicationFlags.NON_UNIQUE)
		settings = ExMortisSettings()

		if settings.can_save:
			widget = Gtk.CheckButton.new_with_label(
				_("Restore windows between sessions")
			)

			if not is_primary:
				widget.set_sensitive(False)

			create_bindings(
				self, settings, widget,
				{'restore_between_sessions': 'active'},
				GObject.BindingFlags.BIDIRECTIONAL
			)

			widget.set_active(settings.restore_between_sessions)
			widget._settings = settings

		else:
			widget = Gtk.Label.new(_("Could not load settings schema"))

		box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
		box.set_border_width(5)
		box.add(widget)

		return box

