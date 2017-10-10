# -*- coding: utf-8 -*-
#
# windowmanager.py
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

from gi.repository import GObject, GLib, Gedit
from .windowstate import ExMortisWindowState
from .utils import connect_handlers, disconnect_handlers
from . import log


class ExMortisWindowManager(GObject.Object):

	__gtype_name__ = 'ExMortisWindowManager'


	def __init__(self):
		GObject.Object.__init__(self)

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		self._windows = {}
		self._debounce_ids = {}

	def cleanup(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		windows = self._windows.keys()

		for window in windows:
			self.untrack_window(window)

		self._windows = None
		self._debounce_ids = None


	# signals

	@GObject.Signal(arg_types=(Gedit.Window, Gedit.Tab))
	def tab_added(self, window, tab):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

	@GObject.Signal(arg_types=(Gedit.Window, Gedit.Tab))
	def tab_removed(self, window, tab):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

	@GObject.Signal(arg_types=(Gedit.Window,))
	def tabs_reordered(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

	@GObject.Signal(arg_types=(Gedit.Window, Gedit.Tab))
	def active_tab_changed(self, window, tab):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

	@GObject.Signal(arg_types=(Gedit.Window, Gedit.Tab))
	def tab_updated(self, window, tab):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))


	# tracking / untracking windows

	def track_window(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if window in self._windows:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("window already being tracked"))

			return

		state = ExMortisWindowState()
		state.save_window(window)

		side_panel = window.get_side_panel()
		bottom_panel = window.get_bottom_panel()
		hpaned = window.get_template_child(Gedit.Window, 'hpaned')
		vpaned = window.get_template_child(Gedit.Window, 'vpaned')

		connect_handlers(
			self, window,
			[
				'tab-added',
				'tab-removed',
				'tabs-reordered',
				'active-tab-changed',
				'size-allocate',
				'window-state-event',
			],
			'window',
			state
		)
		connect_handlers(
			self, side_panel,
			[
				'notify::visible-child-name',
				'notify::visible'
			],
			'side_panel',
			window, state
		)
		connect_handlers(
			self, bottom_panel,
			[
				'notify::visible-child-name',
				'notify::visible'
			],
			'bottom_panel',
			window, state
		)
		connect_handlers(
			self, hpaned,
			[
				'notify::position'
			],
			'hpaned',
			window, state
		)
		connect_handlers(
			self, vpaned,
			[
				'notify::position'
			],
			'vpaned',
			window, state
		)

		self._windows[window] = (
			state,
			{
				'side_panel': side_panel,
				'bottom_panel': bottom_panel,
				'hpaned': hpaned,
				'vpaned': vpaned
			}
		)

		for document in window.get_documents():
			self.track_tab(window, Gedit.Tab.get_from_document(document), state)

	def untrack_window(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if window not in self._windows:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("unknown window"))

			return

		state, widgets = self._windows[window]
		hpaned = widgets['hpaned']
		vpaned = widgets['vpaned']

		for document in window.get_documents():
			self.untrack_tab(window, Gedit.Tab.get_from_document(document), state)

		self.cancel_debounce(window)
		self.cancel_debounce(hpaned)
		self.cancel_debounce(vpaned)

		disconnect_handlers(self, window)
		disconnect_handlers(self, widgets['side_panel'])
		disconnect_handlers(self, widgets['bottom_panel'])
		disconnect_handlers(self, hpaned)
		disconnect_handlers(self, vpaned)

		del self._windows[window]

	def track_tab(self, window, tab, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		connect_handlers(self, tab, ['notify::name'], 'tab', window, state)

	def untrack_tab(self, window, tab, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		disconnect_handlers(self, tab)


	# window state

	def new_window_state(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		return ExMortisWindowState()

	def get_window_state(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if window not in self._windows:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("unknown window"))

			return None

		state, widgets = self._windows[window]

		return state

	def export_window_state(self, window, forget_notebooks=False, forget_tabs=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, forget_notebooks=%s, forget_tabs=%s", window, forget_notebooks, forget_tabs))

		state = self.get_window_state(window)

		if not state:
			return None

		export_state = ExMortisWindowState.clone(state)

		if forget_notebooks:
			export_state.forget_notebooks()

		if forget_tabs:
			export_state.forget_tabs()

		return export_state

	def import_window_state(self, window, import_state, is_new_window=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, is_new_window=%s", window, is_new_window))

		state = self.get_window_state(window)

		if not state:
			return

		import_state.apply_window(window, is_new_window)

	def save_to_window_state(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state = self.get_window_state(window)

		if state:
			state.save_window(window)

	def restore_from_window_state(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state = self.get_window_state(window)

		if state:
			state.apply_window(window)

	def open_new_window_with_window_state(self, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		app = Gedit.App.get_default()
		window = Gedit.App.create_window(app, None)

		self.import_window_state(window, state, True)

		window.present()

		return window


	# signal handlers

	def on_window_tab_added(self, window, tab, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		self.track_tab(window, tab, state)

		state.update_structure(window)

		self.emit('tab-added', window, tab)

	def on_window_tab_removed(self, window, tab, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		self.untrack_tab(window, tab, state)

		state.update_structure(window)

		self.emit('tab-removed', window, tab)

	def on_window_tabs_reordered(self, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.update_structure(window)

		self.emit('tabs-reordered', window)

	def on_window_active_tab_changed(self, window, tab, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		state.save_active_uri(window, tab)

		self.emit('active-tab-changed', window, tab)

	# this signal is emitted way too frequently
	def on_window_size_allocate(self, window, allocation, state):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		self.debounce(window, self.debounce_save_window_size, state)

	def on_window_window_state_event(self, window, event, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.save_window_state(window, event.new_window_state)

	def on_side_panel_notify_visible_child_name(self, side_panel, pspec, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s",window))

		state.save_side_panel_page_name(window)

	def on_side_panel_notify_visible(self, side_panel, pspec, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.save_side_panel_visible(window)

	def on_bottom_panel_notify_visible_child_name(self, bottom_panel, pspec, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.save_bottom_panel_page_name(window)

	def on_bottom_panel_notify_visible(self, bottom_panel, pspec, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.save_bottom_panel_visible(window)

	# this signal could be emitted frequently
	def on_hpaned_notify_position(self, hpaned, pspec, window, state):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		self.debounce(hpaned, self.debounce_save_side_panel_size, window, state)

	# this signal could be emitted frequently
	def on_vpaned_notify_position(self, vpaned, pspec, window, state):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		self.debounce(vpaned, self.debounce_save_bottom_panel_size, window, state)

	def on_tab_notify_name(self, tab, pspec, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		state.save_uri(window, tab)

		self.emit('tab-updated', window, tab)


	# debounced handlers

	def debounce_save_window_size(self, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.save_size(window)

		# we tried tracking notebook size-allocate signals
		# but when we untrack, the handler was already disconnected for some reason
		# and there were gtk assertions that repeatedly failed
		# so just call this here
		state.save_notebook_widths(window)

		self.done_debounce(window)

		return False

	def debounce_save_side_panel_size(self, hpaned, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.save_side_panel_size(window)

		self.done_debounce(hpaned)

		return False

	def debounce_save_bottom_panel_size(self, vpaned, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.save_bottom_panel_size(window)

		self.done_debounce(vpaned)

		return False


	# debouncing

	def debounce(self, obj, fn, *args):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", obj))

		self.cancel_debounce(obj)

		self._debounce_ids[obj] = GLib.timeout_add(1000, fn, obj, *args)

	def cancel_debounce(self, obj):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", obj))

		if obj in self._debounce_ids:
			GLib.source_remove(self._debounce_ids[obj])
			del self._debounce_ids[obj]

	def done_debounce(self, obj):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", obj))

		if obj in self._debounce_ids:
			del self._debounce_ids[obj]

