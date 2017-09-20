# -*- coding: utf-8 -*-
#
# quitting.py
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

from gi.repository import GObject, Gedit
from . import window_info


class Quitting(object):
	def do_activate_quitting(self):
		Gedit.debug_plugin_message("")

		self._opened = {}
		self._quitting = None
		self._restore_window = None
		self._restore_handler = None

	def do_deactivate_quitting(self):
		Gedit.debug_plugin_message("")

		self._opened = None
		self._quitting = None
		self._restore_window = None
		self._restore_handler = None


	# opened

	def get_opened(self):
		Gedit.debug_plugin_message("")

		return self._opened

	def update_opened(self, window):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		window_hash = hash(window)
		app = Gedit.App.get_default()

		if window in app.get_main_windows():
			self._opened[window_hash] = window_info.filter_uris(*window_info.get_info(window))

		elif window_hash in self._opened:
			del self._opened[window_hash]


	# quitting

	def is_quitting(self):
		return self._quitting is not None

	def start_quitting(self):
		Gedit.debug_plugin_message("")

		app = Gedit.App.get_default()

		self._quitting = {
			hash(window) : window_info.get_info(window)
			for window in app.get_main_windows()
		}

	def cancel_quitting(self):
		Gedit.debug_plugin_message("")

		if self.is_quitting():
			Gedit.debug_plugin_message("quitting started, cancelling")

			self._quitting = None

	def update_quitting(self, window, tab):
		Gedit.debug_plugin_message("Window: %s, Tab: %s", hex(hash(window)), hex(hash(tab)))

		if self.is_quitting():
			window_hash = hash(window)
			if window_hash in self._quitting:
				window_info.update_info(*self._quitting[window_hash], tab)

			else:
				Gedit.debug_plugin_message("quitting started but window is not tracked?")

	def end_quitting(self):
		Gedit.debug_plugin_message("")

		window_uris_map = None

		if self.is_quitting():
			window_uris_map = {
				window_hash : window_info.filter_uris(*info)
				for window_hash, info in self._quitting.items()
			}

			Gedit.debug_plugin_message("saving %d windows", len(window_uris_map))

			self._quitting = None

		else:
			Gedit.debug_plugin_message("end quitting without starting?")

		return window_uris_map


	# restoring

	def restore_windows(self, window_uris_list):
		Gedit.debug_plugin_message("restoring %d windows", len(window_uris_list))

		for window_uris in window_uris_list:
			window_info.open_uris_in_window(window_uris)

		app = Gedit.App.get_default()
		window = app.get_active_window()

		if window:
			Gedit.debug_plugin_message("waiting for new tab in window %s", hex(hash(window)))

			self._restore_window = window
			self._restore_handler = window.connect('tab-added', self.on_restore_window_tab_added)

	def on_restore_window_tab_added(self, window, tab):
		Gedit.debug_plugin_message("Window: %s, Tab: %s", hex(hash(window)), hex(hash(tab)))

		if (tab.get_document().is_untouched()
				and tab.get_state() is Gedit.TabState.STATE_NORMAL):
			Gedit.debug_plugin_message("closing untouched tab")

			def close_tab():
				window.close_tab(tab)
				return False

			GObject.idle_add(close_tab)

		else:
			Gedit.debug_plugin_message("new tab is not untouched")

		self.teardown_restore_window(window)

	def teardown_restore_window(self, window):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		if window is self._restore_window:
			window.disconnect(self._restore_handler)
			self._restore_window = None
			self._restore_handler = None
