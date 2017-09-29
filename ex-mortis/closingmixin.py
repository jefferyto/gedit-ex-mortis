# -*- coding: utf-8 -*-
#
# closingmixin.py
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
from .utils import debug_str
from . import log


class ClosingMixin(object):

	def do_activate_closing(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix())

		self._closing = {}
		self._closed = []

	def do_deactivate_closing(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix())

		self._closing = None
		self._closed = None


	# closing

	def is_closing(self, window):
		return window in self._closing

	def start_closing(self, window_manager, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "%s", debug_str(window))

		if self.is_closing(window):
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.prefix() + "already started closing window")

		self._closing[window] = window_manager.export_window_state(window)

	# can be called on non-closing windows
	def cancel_closing(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "%s", debug_str(window))

		if not self.is_closing(window):
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.prefix() + "not closing window")
			return

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "cancelling closing window")

		del self._closing[window]

	# can be called on non-closing windows
	def update_closing(self, window, tab):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "%s, %s", debug_str(window), debug_str(tab))

		if not self.is_closing(window):
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.prefix() + "not closing window")
			return

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "updating closing window")

		state = self._closing[window]
		state.update_uri_from_tab(tab, True)

	def end_closing(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "%s", debug_str(window))

		if not self.is_closing(window):
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.prefix() + "end closing window without starting")
			return

		state = self._closing[window]

		if state.filtered_uris:
			if log.query(log.MESSAGE):
				Gedit.debug_plugin_message(log.prefix() + "window has reopenable files, caching")

			self._closed.append(state)

		else:
			if log.query(log.MESSAGE):
				Gedit.debug_plugin_message(log.prefix() + "window does not have reopenable files, ignoring")

		del self._closing[window]


	# reopening

	def can_reopen(self):
		return len(self._closed) > 0

	def reopen_closed(self, window_manager):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix())

		if not self.can_reopen():
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.prefix() + "do not have closed windows to reopen")
			return

		window_manager.open_new_window_with_window_state(self._closed.pop())

