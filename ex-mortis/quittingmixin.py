# -*- coding: utf-8 -*-
#
# quittingmixin.py
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

from gi.repository import GLib, Gio, Gedit
from .utils import connect_handlers, disconnect_handlers
from . import log


class QuittingMixin(object):

	def do_activate_quitting(self, is_saving_window_states):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("is_saving_window_states=%s", is_saving_window_states))

		self._window_ids = {} if is_saving_window_states else None
		self._quitting = None
		self._restore_windows = None

	def do_deactivate_quitting(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		self.teardown_restore_windows()

		self._window_ids = None
		self._quitting = None
		self._restore_windows = None


	# saving window states

	def is_saving_window_states(self):
		return self._window_ids is not None

	def start_saving_window_states(self, window_manager, settings):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		if self.is_saving_window_states():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("already saving window states"))

			return

		self._window_ids = {}

		app = Gedit.App.get_default()

		for window in app.get_main_windows():
			self.bind_window_settings(window_manager, settings, window)

	def stop_saving_window_states(self, window_manager, settings):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		if not self.is_saving_window_states():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("not saving window states"))

			return

		app = Gedit.App.get_default()

		for window in app.get_main_windows():
			self.unbind_window_settings(window_manager, settings, window)

		self._window_ids = None

	def bind_window_settings(self, window_manager, settings, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not self.is_saving_window_states():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("not saving window states"))

			return

		state = window_manager.get_window_state(window)

		if not state:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("could not get window state"))

			return

		window_id = settings.add_window()
		self._window_ids[window] = window_id

		window_settings = settings.get_window_settings(window_id)

		if not window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("could not get window settings"))

			return

		for param in state.list_properties(): # actually a class method
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
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not self.is_saving_window_states():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("not saving window states"))

			return

		state = window_manager.get_window_state(window)

		if not state:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("could not get window state"))

			return

		if window not in self._window_ids:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("could not find window id"))

			return

		window_id = self._window_ids[window]
		window_settings = settings.get_window_settings(window_id)

		if not window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("could not get window settings"))

			return

		for param in state.list_properties(): # actually a class method
			window_settings.unbind(state, param.name)

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
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		if self.is_quitting():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("already started quitting"))

		app = Gedit.App.get_default()

		self._quitting = {
			window : window_manager.export_window_state(window, True)
			for window in app.get_main_windows()
		}

	# can be called when not quitting
	def cancel_quitting(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		if not self.is_quitting():
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("not quitting"))

			return

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("cancelling quitting"))

		self._quitting = None

	# can be called when not quitting
	def update_quitting(self, window, tab):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		if not self.is_quitting():
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("not quitting"))

			return

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("updating quitting"))

		if window not in self._quitting:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("unknown window"))

			return

		state = self._quitting[window]

		state.save_uri(window, tab)
		state.forget_tab(tab)

	def end_quitting(self, settings, do_save):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("do_save=%s", do_save))

		if not self.is_quitting():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("end quitting without starting"))

			return

		if do_save:
			for window, state in self._quitting.items():
				if state.restore_uris:
					window_id = settings.add_window()
					window_settings = settings.get_window_settings(window_id)

					if not window_settings:
						if log.query(log.WARNING):
							Gedit.debug_plugin_message(log.format("could not get window settings"))
						continue

					for param in state.list_properties(): # actually a class method
						window_settings[param.name] = state.get_property(param.name)

					window_settings['uris'] = state.restore_uris
					window_settings['notebook-widths'] = state.restore_notebook_widths

			if log.query(log.MESSAGE):
				Gedit.debug_plugin_message(log.format("saving %s windows", len(settings.restore_windows)))

		else:
			if log.query(log.MESSAGE):
				Gedit.debug_plugin_message(log.format("not saving windows"))

		self._quitting = None


	# restoring

	def restore_windows(self, window_manager, settings, do_restore):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("do_restore=%s", do_restore))

		states = []
		windows = []

		for window_id in list(settings.restore_windows):
			if do_restore:
				state = window_manager.new_window_state()
				window_settings = settings.get_window_settings(window_id)

				if not window_settings:
					if log.query(log.WARNING):
						Gedit.debug_plugin_message(log.format("could not get window settings"))
					continue

				for param in state.list_properties(): # actually a class method
					state.set_property(
						param.name, window_settings[param.name]
					)

				state.uris = window_settings['uris']
				state.notebook_widths = window_settings['notebook-widths']

				if state.restore_uris:
					states.append(state)

			settings.remove_window(window_id)

		if do_restore:
			if log.query(log.MESSAGE):
				Gedit.debug_plugin_message(log.format("restoring %s windows", len(states)))

			screen_width = window_manager.get_screen_width()
			screen_height = window_manager.get_screen_height()

			for state in states:
				# when gedit goes to open the first blank tab,
				# it tries to find an active window first
				# but it tests for windows in the current screen/workspace/viewport
				# which is in part based on the size of the window
				# so we need to shrink our windows here to fit the screen,
				# otherwise gedit will think they are in a different viewport
				# if the window is too large for the screen,
				# the window manager will (probably?) resize the window to fit anyway
				if state.width > screen_width:
					state.width = screen_width
				if state.height > screen_height:
					state.height = screen_height

				windows.append(window_manager.open_new_window_with_window_state(state))

			self._restore_windows = {}

			# the window manager can choose to make another window active
			# rather than the active window at the end of this process
			# so listen for new tab on all windows
			for window, state in zip(windows, states):
				self.setup_restore_window(window, state)

		else:
			if log.query(log.MESSAGE):
				Gedit.debug_plugin_message(log.format("not restoring windows"))

	def setup_restore_window(self, window, state=None):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if self._restore_windows is None:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("not handling restore windows"))

			return

		if window in self._restore_windows:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("restore window already set up"))

			return

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("setting up restore window"))

		self._restore_windows[window] = window.connect(
			'tab-added', self.on_restore_window_tab_added, state
		)

	def teardown_restore_windows(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		if self._restore_windows is None:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("not handling restore windows"))

			return

		for window in list(self._restore_windows.keys()):
			self.teardown_restore_window(window)

		self._restore_windows = None

	def teardown_restore_window(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if self._restore_windows is None:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("not handling restore windows"))

			return

		if window not in self._restore_windows:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("not restore window or restore window already torn down"))

			return

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("tearing down restore window"))

		window.disconnect(self._restore_windows[window])

		del self._restore_windows[window]

	def on_restore_window_tab_added(self, window, tab, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		if (tab.get_document().is_untouched()
				and tab.get_state() == Gedit.TabState.STATE_NORMAL):
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("closing untouched tab"))

			def close_tab():
				window.close_tab(tab)

				if not window.get_active_tab():
					window.close()

				elif state:
					state.apply_active_uri(window)

				return False

			GLib.idle_add(close_tab)

		else:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("new tab is not untouched"))

		self.teardown_restore_windows()

