# -*- coding: utf-8 -*-
#
# quittingmixin.py
# This file is part of Ex-Mortis, a plugin for gedit
#
# Copyright (C) 2017-2019, 2023-2024 Jeffery To <jeffery.to@gmail.com>
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
gi.require_version('GObject', '2.0')
gi.require_version('GLib', '2.0')
gi.require_version('Gedit', '3.0')
gi.require_version('Gio', '2.0')

from gi.repository import GObject, GLib, Gedit, Gio
from .utils import connect_handlers, disconnect_handlers
from . import log


class ExMortisAppActivatableQuittingMixin(object):

	def do_activate_quitting(self, is_saving_window_states):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("is_saving_window_states=%s", is_saving_window_states))

		self._window_ids = {} if is_saving_window_states else None
		self._quitting = None
		self._restore_states = None
		self._restore_windows = None

	def do_deactivate_quitting(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		self.teardown_restore_windows()

		self._window_ids = None
		self._quitting = None
		self._restore_states = None
		self._restore_windows = None


	# saving window states

	def is_saving_window_states(self):
		return self._window_ids is not None

	def start_saving_window_states(self, window_manager, settings):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		if self.is_saving_window_states():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Already saving window states"))

			return

		self._window_ids = {}

		for window in self.app.get_main_windows():
			self.bind_window_settings(window_manager, settings, window)

	def stop_saving_window_states(self, window_manager, settings):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		if not self.is_saving_window_states():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Not saving window states"))

			return

		for window in self.app.get_main_windows():
			try:
				self.unbind_window_settings(window_manager, settings, window)
			except ValueError: # gedit 3.14
				pass

		self._window_ids = None

	def bind_window_settings(self, window_manager, settings, window):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not self.is_saving_window_states():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Not saving window states"))

			return

		state = window_manager.get_window_state(window)

		if not state:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Could not get state for %s", window))

			return

		window_id = settings.add_window()
		self._window_ids[window] = window_id

		window_settings = settings.get_window_settings(window_id)

		if not window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Could not get settings for %s", window))

			return

		try:
			params = state.list_properties()
		except AttributeError: # gedit 3.12
			params = GObject.list_properties(state)

		for param in params:
			# this also immediately sets the settings based on the state values
			window_settings.bind(
				param.name,
				state, param.name,
				Gio.SettingsBindFlags.SET
			)

		connect_handlers(
			self, state,
			[
				'uris-changed',
				'notebook-widths-changed'
			],
			'window_state',
			window_settings
		)

		self.on_window_state_uris_changed(state, window_settings)
		self.on_window_state_notebook_widths_changed(state, window_settings)

	def unbind_window_settings(self, window_manager, settings, window):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not self.is_saving_window_states():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Not saving window states"))

			return

		state = window_manager.get_window_state(window)

		if not state:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Could not get state for %s", window))

			return

		if window not in self._window_ids:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Could not find window id for %s", window))

			return

		window_id = self._window_ids[window]
		window_settings = settings.get_window_settings(window_id)

		if not window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Could not get settings for %s", window))

			return

		try:
			params = state.list_properties()
		except AttributeError: # gedit 3.12
			params = GObject.list_properties(state)

		for param in params:
			try:
				window_settings.unbind(state, param.name)
			except ValueError: # gedit 3.14
				pass

		disconnect_handlers(self, state)

		settings.remove_window(window_id)

		del self._window_ids[window]

	def on_window_state_uris_changed(self, state, window_settings):
		window_settings['uris'] = state.restore_uris

	def on_window_state_notebook_widths_changed(self, state, window_settings):
		window_settings['notebook-widths'] = state.restore_notebook_widths


	# quitting

	def is_quitting(self):
		return self._quitting is not None

	def start_quitting(self, window_manager):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		if self.is_quitting():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Already started quitting"))

		self._quitting = {
			window : window_manager.export_window_state(window, forget_notebooks=True)
			for window in self.app.get_main_windows()
		}

	# can be called when not quitting
	def cancel_quitting(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		if not self.is_quitting():
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("Not quitting"))

			return

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("Cancelling quitting"))

		self._quitting = None

	# can be called when not quitting
	def update_quitting(self, window, tab):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		if not self.is_quitting():
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("Not quitting"))

			return

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("Updating quitting"))

		if window not in self._quitting:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Unknown window %s", window))

			return

		state = self._quitting[window]

		state.save_uri(window, tab)
		state.forget_tab(tab)

	def end_quitting(self, settings, do_save):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("do_save=%s", do_save))

		if not self.is_quitting():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("End quitting without starting"))

			return

		if do_save:
			for window, state in self._quitting.items():
				if state.restore_uris:
					window_id = settings.add_window()
					window_settings = settings.get_window_settings(window_id)

					if not window_settings:
						if log.query(log.WARNING):
							Gedit.debug_plugin_message(log.format("Could not get settings for %s", window))
						continue

					try:
						params = state.list_properties()
					except AttributeError: # gedit 3.12
						params = GObject.list_properties(state)

					for param in params:
						window_settings[param.name] = state.get_property(param.name)

					window_settings['uris'] = state.restore_uris
					window_settings['notebook-widths'] = state.restore_notebook_widths

			if log.query(log.MESSAGE):
				Gedit.debug_plugin_message(log.format("Saving %s windows", len(settings.restore_windows)))

		else:
			if log.query(log.MESSAGE):
				Gedit.debug_plugin_message(log.format("Not saving windows"))

		self._quitting = None


	# restoring

	def prepare_restore_data(self, window_manager, settings):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		states = []

		for window_id in settings.restore_windows:
			state = window_manager.new_window_state()
			window_settings = settings.get_window_settings(window_id)

			if not window_settings:
				if log.query(log.WARNING):
					Gedit.debug_plugin_message(log.format("Could not get settings for %s", window))
				continue

			try:
				params = state.list_properties()
			except AttributeError: # gedit 3.12
				params = GObject.list_properties(state)

			for param in params:
				state.set_property(
					param.name, window_settings[param.name]
				)

			state.uris = window_settings['uris']
			state.notebook_widths = window_settings['notebook-widths']

			if state.restore_uris:
				states.append(state)

		settings.remove_windows()

		if not states:
			if log.query(log.MESSAGE):
				Gedit.debug_plugin_message(log.format("No windows to restore"))

			return

		if log.query(log.MESSAGE):
			Gedit.debug_plugin_message(log.format("Will restore %s windows", len(states)))

		screen_width = window_manager.get_screen_width()
		screen_height = window_manager.get_screen_height()

		for state in states:
			# when gedit goes to open the first blank tab,
			# it tries to find an active window first
			# but it tests for windows in the current screen/workspace/viewport
			# which is in part based on the size of the window
			# so we need to shrink our windows here to fit the screen,
			# otherwise gedit will think they are in a different viewport
			# (if the window is too large for the screen,
			# the window manager will probably resize the window to fit anyway)
			if state.width > screen_width:
				state.side_panel_size = round((state.side_panel_size / state.width) * screen_width)
				state.width = screen_width
			if state.height > screen_height:
				state.bottom_panel_size = round((state.bottom_panel_size / state.height) * screen_height)
				state.height = screen_height

		self._restore_states = states
		self._restore_windows = {}

	def discard_restore_data(self, settings):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		settings.remove_windows()

		if log.query(log.MESSAGE):
			Gedit.debug_plugin_message(log.format("Not restoring windows"))

	def setup_restore_window(self, window_manager, window):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		if self._restore_windows is None:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("Not handling restore windows"))

			return

		if window in self._restore_windows:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("Already set up %s", window))

			return

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("Setting up %s", window))

		self._restore_windows[window] = window.connect(
			'tab-added', self.on_restore_window_tab_added, window_manager
		)

	def teardown_restore_windows(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		if self._restore_windows is None:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("Not handling restore windows"))

			return

		for window in list(self._restore_windows.keys()):
			self.teardown_restore_window(window)

		self._restore_windows = None

	def teardown_restore_window(self, window):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		if self._restore_windows is None:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("Not handling restore windows"))

			return

		if window not in self._restore_windows:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("Not restore window or already torn down %s", window))

			return

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("Tearing down %s", window))

		window.disconnect(self._restore_windows[window])

		del self._restore_windows[window]

	def on_restore_window_tab_added(self, window, tab, window_manager):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		self.teardown_restore_windows()

		def do_restore_windows():
			self.restore_windows(window_manager, window, tab)

			return False

		GLib.idle_add(do_restore_windows)

	def restore_windows(self, window_manager, window, tab):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		active_tab = window.get_active_tab()
		num_tabs = len(active_tab.get_parent().get_children())

		document = tab.get_document()
		try:
			is_untouched = document.is_untouched() # removed in gedit 44
		except AttributeError:
			is_untouched = document_is_untouched(document)

		try:
			normal_state = Gedit.TabState.NORMAL
		except AttributeError:
			normal_state = Gedit.TabState.STATE_NORMAL # before gedit 47

		is_single_empty_tab = (
			num_tabs == 1
			and tab is active_tab
			and is_untouched
			and tab.get_state() == normal_state
		)

		# if there is only one empty tab, let gedit reuse it when opening files
		# otherwise, open a new tab to be (re)used
		# this protects the new tab that was added if gedit was run with
		# --new-document and one or more files to open

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("is_single_empty_tab=%s", is_single_empty_tab))

		if not is_single_empty_tab:
			window.create_tab(True)

		state = self._restore_states.pop()
		window_manager.import_window_state(window, state)

		for state in self._restore_states:
			window_manager.open_new_window_with_window_state(state)

		self._restore_states = None

		if not is_single_empty_tab:
			window.set_active_tab(active_tab)
			window.present()

# based on tepl_buffer_is_untouched() in tepl-buffer.c
def document_is_untouched(document):
	return (
		document.get_char_count() == 0
		and not document.get_modified()
		and not document.can_undo()
		and not document.can_redo()
		and document.get_file().get_location() is None
	)

