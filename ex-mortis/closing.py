# -*- coding: utf-8 -*-
#
# closing.py
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

from gi.repository import Gedit
from . import window_info


class Closing(object):
	def do_activate_closing(self):
		Gedit.debug_plugin_message("")

		self._closing = {}
		self._closed = []

	def do_deactivate_closing(self):
		Gedit.debug_plugin_message("")

		self._closing = None
		self._closed = None


	# closing

	def is_closing(self, window):
		return hash(window) in self._closing

	def start_closing(self, window):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		self._closing[hash(window)] = window_info.get_info(window)

	def cancel_closing(self, window):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		if self.is_closing(window):
			Gedit.debug_plugin_message("closing window started, cancelling")

			del self._closing[hash(window)]

	def update_closing(self, window, tab):
		Gedit.debug_plugin_message("Window: %s, Tab: %s", hex(hash(window)), hex(hash(tab)))

		if self.is_closing(window):
			window_info.update_info(*self._closing[hash(window)], tab)

	def end_closing(self, window):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		if self.is_closing(window):
			window_uris = window_info.filter_uris(*self._closing[hash(window)])

			if window_uris:
				Gedit.debug_plugin_message("window has reopenable files, caching")

				self._closed.append(window_uris)

			else:
				Gedit.debug_plugin_message("window does not have reopenable files, ignoring")

			del self._closing[hash(window)]

		else:
			Gedit.debug_plugin_message("end closing window without starting?")


	# reopening

	def has_closed(self):
		return len(self._closed) > 0

	def reopen_closed(self):
		Gedit.debug_plugin_message("")

		if self.has_closed():
			Gedit.debug_plugin_message("have cached windows, reopening")

			window_info.open_uris_in_window(self._closed.pop())

		else:
			Gedit.debug_plugin_message("do not have cached windows, how did we get here?")
