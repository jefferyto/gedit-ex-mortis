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

import gettext
import os.path
from gi.repository import GObject, Gtk, Gio, Gedit, PeasGtk
from .closing import Closing
from .existing import Existing
from .quitting import Quitting
from .settings import Settings
from .utils import connect_handlers, disconnect_handlers

GETTEXT_PACKAGE = 'gedit-ex-mortis'
BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
	gettext.bindtextdomain(GETTEXT_PACKAGE, LOCALE_PATH)
	_ = lambda s: gettext.dgettext(GETTEXT_PACKAGE, s);
except:
	_ = lambda s: s


class ExMortisAppActivatable(
		GObject.Object, Gedit.AppActivatable,
		Existing, Closing, Quitting, Settings):
	__gtype_name__ = 'ExMortisAppActivatable'

	app = GObject.property(type=Gedit.App)


	# gedit plugin api

	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		Gedit.debug_plugin_message("")

		app = self.app

		# reopen action
		reopen_action = Gio.SimpleAction.new('reopen-closed-window', None)
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
		custom_quit_action = Gio.SimpleAction.new('quit', None)
		connect_handlers(self, custom_quit_action, ['activate'], 'quit')
		app.remove_action('quit')
		app.add_action(custom_quit_action)

		# app
		connect_handlers(
			self, app,
			['window-added', 'window-removed', 'shutdown'],
			'app'
		)

		self._reopen_action = reopen_action
		self._menu_ext = menu_ext
		self._original_quit_action = original_quit_action
		self._custom_quit_action = custom_quit_action

		self.do_activate_existing()
		self.do_activate_closing()
		self.do_activate_quitting()
		self.do_activate_settings()

		# settings
		settings = self.get_settings()

		if settings:
			connect_handlers(
				self, settings,
				[self.get_settings_signal_changed_restore_between_sessions()],
				self.on_settings_changed_restore_between_sessions
			)

		# windows
		windows = app.get_main_windows()

		if windows:
			# plugin activated during existing session
			for window in windows:
				self.setup_window(window, True)

		elif self.get_settings_restore_between_sessions():
			# plugin activated during app startup
			self.restore_windows(self.get_settings_restore_uris())

	def do_deactivate(self):
		Gedit.debug_plugin_message("")

		app = self.app

		# app
		disconnect_handlers(self, app)

		# windows
		for window in app.get_main_windows():
			self.teardown_window(window)

		# settings
		settings = self.get_settings()
		if settings:
			disconnect_handlers(self, settings)

		# quit action
		app.remove_action('quit')
		app.add_action(self._original_quit_action)
		disconnect_handlers(self, self._custom_quit_action)

		# reopen menu item
		app.set_accels_for_action('app.reopen-closed-window', [])

		# reopen action
		app.remove_action('reopen-closed-window')

		self._reopen_action = None
		self._menu_ext = None
		self._original_quit_action = None
		self._custom_quit_action = None

		self.do_deactivate_existing()
		self.do_deactivate_closing()
		self.do_deactivate_quitting()
		self.do_deactivate_settings()


	# window setup

	def setup_window(self, window, is_existing=False):
		Gedit.debug_plugin_message("Window: %s, is_existing: %s", hex(hash(window)), is_existing)

		if is_existing:
			info_bar, quit_response_id, default_response_id = self.create_existing_info_bar()

			connect_handlers(
				self, info_bar,
				['response'],
				'existing_window_info_bar',
				window, quit_response_id
			)

			hpaned = window.get_template_child(Gedit.Window, 'hpaned')
			main_box = hpaned.get_parent()
			num_children = len(main_box.get_children())

			main_box.pack_start(info_bar, False, False, 0)
			main_box.reorder_child(info_bar, num_children - 1)

			# must be done after the info bar is added to the window
			info_bar.set_default_response(default_response_id)

			info_bar.show()

			self.add_existing(window, info_bar)

		connect_handlers(
			self, window,
			['delete-event', 'tab-added', 'tab-removed', 'tabs-reordered'],
			'window'
		)

		for document in window.get_documents():
			self.setup_tab(window, Gedit.Tab.get_from_document(document))

		self.update_and_save_opened(window)

	def teardown_window(self, window):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		if self.is_existing(window):
			info_bar = self.get_existing_info_bar(window)
			disconnect_handlers(self, info_bar)
			info_bar.destroy()

			self.remove_existing(window)

		disconnect_handlers(self, window)

		self.teardown_restore_window(window)

		for document in window.get_documents():
			self.teardown_tab(window, Gedit.Tab.get_from_document(document))

		self.update_and_save_opened(window)


	# tab setup

	def setup_tab(self, window, tab):
		Gedit.debug_plugin_message("Window: %s, Tab: %s", hex(hash(window)), hex(hash(tab)))

		connect_handlers(self, tab, ['notify::name'], 'tab', window)

		self.update_and_save_opened(window)

	def teardown_tab(self, window, tab):
		Gedit.debug_plugin_message("Window: %s, Tab: %s", hex(hash(window)), hex(hash(tab)))

		disconnect_handlers(self, tab)

		self.update_and_save_opened(window)


	# app signal handlers
	# preferences window also triggers window-added / window-removed

	def on_app_window_added(self, app, window):
		if isinstance(window, Gedit.Window):
			Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

			self.cancel_quitting()

			self.setup_window(window)

	def on_app_window_removed(self, app, window):
		if isinstance(window, Gedit.Window):
			Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

			if not self.is_existing(window):
				self.end_closing(window)
				self.update_reopen_action_enabled()

			self.teardown_window(window)

	def on_app_shutdown(self, app):
		Gedit.debug_plugin_message("")

		self.end_and_save_quitting()


	# window signal handlers

	def on_window_delete_event(self, window, event):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		# closing the only window also quits the app
		if len(self.app.get_main_windows()) == 1:
			self.start_quitting()

		# this handler would not be called on an existing window anyway
		# but for completeness sake...
		if not self.is_existing(window):
			self.start_closing(window)

		return False

	def on_window_tab_added(self, window, tab):
		Gedit.debug_plugin_message("Window: %s, Tab: %s", hex(hash(window)), hex(hash(tab)))

		if not self.is_existing(window):
			self.cancel_closing(window)

		self.cancel_quitting()

		self.setup_tab(window, tab)

	def on_window_tab_removed(self, window, tab):
		Gedit.debug_plugin_message("Window: %s, Tab: %s", hex(hash(window)), hex(hash(tab)))

		if not self.is_existing(window):
			self.update_closing(window, tab)

		self.update_quitting(window, tab)

		self.teardown_tab(window, tab)

	def on_window_tabs_reordered(self, window):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		if not self.is_existing(window):
			self.cancel_closing(window)

		self.cancel_quitting()

		self.update_and_save_opened(window)


	# tab signal handlers

	def on_tab_notify_name(self, tab, pspec, window):
		Gedit.debug_plugin_message("Window: %s, Tab: %s", hex(hash(window)), hex(hash(tab)))

		self.update_and_save_opened(window)


	# existing window signal handlers

	def on_existing_window_info_bar_response(self, info_bar, response_id, window, quit_response_id):
		Gedit.debug_plugin_message("Window: %s, Response id: %s", hex(hash(window)), response_id)

		info_bar.hide()

		if response_id == quit_response_id:
			self.app.activate_action('quit')


	# settings signal handlers

	def on_settings_changed_restore_between_sessions(self, settings, prop):
		is_enabled = self.get_settings_restore_between_sessions()

		Gedit.debug_plugin_message("%s", is_enabled)

		self.save_opened()


	# action signal handlers

	def on_reopen_activate(self, action, parameter):
		Gedit.debug_plugin_message("")

		self.reopen_closed()
		self.update_reopen_action_enabled()

	def on_quit_activate(self, action, parameter):
		Gedit.debug_plugin_message("")

		self.start_quitting()

		for window in self.app.get_main_windows():
			if not self.is_existing(window):
				self.start_closing(window)

		self.really_quit()


	# closing helpers

	def update_reopen_action_enabled(self):
		is_enabled = self.has_closed()

		Gedit.debug_plugin_message("%s", is_enabled)

		self._reopen_action.set_enabled(is_enabled)


	# quitting helpers

	def update_and_save_opened(self, window):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		self.update_opened(window)
		self.save_opened()

	def save_opened(self):
		Gedit.debug_plugin_message("")

		window_uris_map = self.get_opened()
		self.set_settings_restore_uris(window_uris_map)

	def end_and_save_quitting(self):
		Gedit.debug_plugin_message("")

		window_uris_map = self.end_quitting()
		self.set_settings_restore_uris(window_uris_map)

	def really_quit(self):
		Gedit.debug_plugin_message("")

		self._original_quit_action.activate()


class ExMortisConfigurable(GObject.Object, PeasGtk.Configurable, Settings):
	__gtype_name__ = 'ExMortisConfigurable'

	def do_create_configure_widget(self):
		Gedit.debug_plugin_message("")

		self.do_activate_settings()

		settings = self.get_settings()

		if settings:
			widget = Gtk.CheckButton(_("Restore windows between sessions"))

			connect_handlers(
				self, widget,
				['toggled'],
				self.on_configure_check_button_toggled_restore_between_sessions
			)

			connect_handlers(
				self, settings,
				[self.get_settings_signal_changed_restore_between_sessions()],
				self.on_configure_settings_changed_restore_between_sessions,
				widget
			)

			widget.set_active(self.get_settings_restore_between_sessions())

		else:
			widget = Gtk.Box()
			widget.add(Gtk.Label(_("Could not load settings schema")))

		widget.set_border_width(5)

		return widget

	def on_configure_check_button_toggled_restore_between_sessions(self, check_button):
		is_enabled = check_button.get_active()

		Gedit.debug_plugin_message("%s", is_enabled)

		self.set_settings_restore_between_sessions(is_enabled)

	def on_configure_settings_changed_restore_between_sessions(self, settings, prop, check_button):
		is_enabled = self.get_settings_restore_between_sessions()

		Gedit.debug_plugin_message("%s", is_enabled)

		check_button.set_active(is_enabled)
