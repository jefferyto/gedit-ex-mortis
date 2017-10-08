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

from gi.repository import GObject, GLib, Gdk, Gio, Gedit
from .utils import connect_handlers, disconnect_handlers, debug_str
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

		self._windows[window] = (state, side_panel, bottom_panel, hpaned, vpaned)

		for document in window.get_documents():
			self.track_tab(window, Gedit.Tab.get_from_document(document), state)

	def untrack_window(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if window not in self._windows:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("unknown window"))

			return

		state, side_panel, bottom_panel, hpaned, vpaned = self._windows[window]

		self.cancel_debounce(window)
		self.cancel_debounce(hpaned)
		self.cancel_debounce(vpaned)

		disconnect_handlers(self, window)
		disconnect_handlers(self, side_panel)
		disconnect_handlers(self, bottom_panel)
		disconnect_handlers(self, hpaned)
		disconnect_handlers(self, vpaned)

		for document in window.get_documents():
			self.untrack_tab(window, Gedit.Tab.get_from_document(document), state)

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

		state, side_panel, bottom_panel, hpaned, vpaned = self._windows[window]

		return state

	def export_window_state(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state = self.get_window_state(window)

		return ExMortisWindowState.clone(state) if state else None

	def import_window_state(self, window, state, set_default_size=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, set_default_size=%s", window, set_default_size))

		if window not in self._windows:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("unknown window"))

			return

		state.apply_size(window, set_default_size)

		window.show()

		state.apply_window(window, True)

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

		state.save_uris(window)

		self.emit('tab-added', window, tab)

	def on_window_tab_removed(self, window, tab, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		self.untrack_tab(window, tab, state)

		state.save_uris(window)

		self.emit('tab-removed', window, tab)

	def on_window_tabs_reordered(self, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.save_uris(window)

		self.emit('tabs-reordered', window)

	def on_window_active_tab_changed(self, window, tab, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		state.save_active_uri(window)

		self.emit('active-tab-changed', window, tab)

	def on_tab_notify_name(self, tab, pspec, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, tab))

		state.update_uri_from_tab(window, tab)

		self.emit('tab-updated', window, tab)

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

		self.debounce(hpaned, self.debounce_save_hpaned_position, window, state)

	# this signal could be emitted frequently
	def on_vpaned_notify_position(self, vpaned, pspec, window, state):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		self.debounce(vpaned, self.debounce_save_vpaned_position, window, state)


	# debounced handlers

	def debounce_save_window_size(self, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not state.maximized and not state.fullscreen:
			state.save_size(window)

		self.done_debounce(window)

		return False

	def debounce_save_hpaned_position(self, hpaned, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.save_hpaned_position(window)

		self.done_debounce(hpaned)

		return False

	def debounce_save_vpaned_position(self, vpaned, window, state):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		state.save_vpaned_position(window)

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


class ExMortisWindowState(GObject.Object):

	__gtype_name__ = 'ExMortisWindowState'

	active_uri = GObject.Property(type=str, default='')

	width = GObject.Property(type=int, default=0)

	height = GObject.Property(type=int, default=0)

	maximized = GObject.Property(type=bool, default=False)

	fullscreen = GObject.Property(type=bool, default=False)

	side_panel_page_name = GObject.Property(type=str, default='')

	side_panel_visible = GObject.Property(type=bool, default=False)

	bottom_panel_page_name = GObject.Property(type=str, default='')

	bottom_panel_visible = GObject.Property(type=bool, default=False)

	hpaned_position = GObject.Property(type=int, default=0)

	vpaned_position = GObject.Property(type=int, default=0)


	def __init__(self):
		GObject.Object.__init__(self)

		self._uris = []
		self._filtered_uris = []
		self._tab_map = {}
		self._active_tab = None


	# class methods

	@classmethod
	def clone(cls, source):
		clone = cls()

		for param in cls.list_properties():
			clone.set_property(param.name, source.get_property(param.name))

		clone.uris = source.uris
		clone.tab_map = source.tab_map

		clone._active_tab = source._active_tab

		return clone


	# properties

	@property
	def uris(self):
		return copy_uris(self._uris)

	@uris.setter
	def uris(self, value):
		uris = copy_uris(value)

		if uris != self._uris:
			self._uris = uris

			self.emit('uris-changed')

	@property
	def filtered_uris(self):
		return copy_uris(self._filtered_uris)

	@property
	def tab_map(self):
		return copy_tab_map(self._tab_map)

	@tab_map.setter
	def tab_map(self, value):
		self._tab_map = copy_tab_map(value)


	# signals

	@GObject.Signal
	def uris_changed(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		filtered = [[uri for uri in uris if uri] for uris in self._uris]
		self._filtered_uris = [uris for uris in filtered if uris]


	# saving / applying windows

	def save_window(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		self.save_uris(window)
		self.save_active_uri(window)
		self.save_size(window)
		self.save_window_state(window)
		self.save_side_panel_page_name(window)
		self.save_side_panel_visible(window)
		self.save_bottom_panel_page_name(window)
		self.save_bottom_panel_visible(window)
		self.save_hpaned_position(window)
		self.save_vpaned_position(window)

	def apply_window(self, window, skip_size=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, skip_size=%s", window, skip_size))

		self.apply_uris(window)
		self.apply_active_uri(window)
		if not skip_size:
			self.apply_size(window)
		self.apply_window_state(window)
		self.apply_side_panel_page_name(window)
		self.apply_side_panel_visible(window)
		self.apply_bottom_panel_page_name(window)
		self.apply_bottom_panel_visible(window)
		self.apply_hpaned_position(window)
		self.apply_vpaned_position(window)


	# window uris

	def save_uris(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		uris = []
		notebook_map = {}
		tab_map = {}

		for document in window.get_documents():
			tab = Gedit.Tab.get_from_document(document)
			notebook = tab.get_parent()

			if notebook not in notebook_map:
				notebook_map[notebook] = len(uris)
				uris.append([])

			notebook_index = notebook_map[notebook]
			notebook_uris = uris[notebook_index]

			tab_index = len(notebook_uris)
			notebook_uris.append(get_tab_uri(tab))

			tab_map[tab] = (notebook_index, tab_index)

		self._tab_map = tab_map

		if uris == self._uris:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("saving uris=%s", uris))

		self._uris = uris

		self.emit('uris-changed')

		return True

	def update_uri_from_tab(self, window, tab, forget_tab=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s, forget_tab=%s", window, tab, forget_tab))

		# active uri

		if tab is self._active_tab:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("active tab"))

			self.save_active_uri(window, tab)

			if forget_tab:
				self._active_tab = None

		else:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("not active tab"))

		# uris

		if tab not in self._tab_map:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("not in tab map"))

			return False

		notebook_index, tab_index = self._tab_map[tab]

		uri = get_tab_uri(tab)

		if forget_tab:
			del self._tab_map[tab]

		if uri == self._uris[notebook_index][tab_index]:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("saving uri=%s", uri))

		self._uris[notebook_index][tab_index] = uri

		self.emit('uris-changed')

		return True

	def apply_uris(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		uris = self._filtered_uris

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("uris=%s", uris))

		if uris:
			documents = window.get_documents()
			create_notebook = False

			if documents:
				window.set_active_tab(Gedit.Tab.get_from_document(documents[-1]))

			for notebook_uris in uris:
				if create_notebook:
					window.activate_action('new-tab-group')

				locations = [
					Gio.File.new_for_uri(uri)
					for uri in notebook_uris
				]

				Gedit.commands_load_locations(window, locations, None, 0, 0)

				create_notebook = True


	# window active uri

	def save_active_uri(self, window, active_tab=None):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, active_tab))

		if active_tab is None:
			active_tab = window.get_active_tab()

		active_uri = get_tab_uri(active_tab) if active_tab else ''
		if not active_uri:
			active_uri = ''

		self._active_tab = active_tab

		if active_uri == self.active_uri:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("saving active_uri=%s", active_uri))

		self.active_uri = active_uri

		return True

	def apply_active_uri(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		active_uri = self.active_uri

		if not active_uri:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no active uri"))

			return

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("applying active_uri=%s", active_uri))

		location = Gio.File.new_for_uri(active_uri)
		tab = window.get_tab_from_location(location)

		if not tab:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("could not find tab for active uri"))

			return

		window.set_active_tab(tab)


	# window size

	def save_size(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		width, height = window.get_size()

		if width == self.width and height == self.height:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if width != self.width:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("saving width=%s", width))

			self.width = width

		if height != self.height:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("saving height=%s", height))

			self.height = height

		return True

	def apply_size(self, window, set_default_size=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, set_default_size=%s", window, set_default_size))

		width = self.width
		height = self.height

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("applying width=%s, height=%s", width, height))

		if set_default_size:
			window.set_default_size(width, height)
		else:
			window.resize(width, height)


	# window state (maximized / fullscreen)

	def save_window_state(self, window, window_state=None):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, window_state=%s", window, window_state))

		if window_state is None:
			gdk_window = window.get_window()

			if not gdk_window:
				if log.query(log.INFO):
					Gedit.debug_plugin_message(log.format("window not yet realized"))

				return False

			window_state = gdk_window.get_state()

		maximized = bool(window_state & Gdk.WindowState.MAXIMIZED)
		fullscreen = bool(window_state & Gdk.WindowState.FULLSCREEN)

		if maximized == self.maximized and fullscreen == self.fullscreen:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if maximized != self.maximized:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("saving maximized=%s", maximized))

			self.maximized = maximized

		if fullscreen != self.fullscreen:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("saving fullscreen=%s", fullscreen))

			self.fullscreen = fullscreen

		return True

	def apply_window_state(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		maximized = self.maximized
		fullscreen = self.fullscreen

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("applying maximized=%s, fullscreen=%s", maximized, fullscreen))

		if maximized:
			window.maximize()
		else:
			window.unmaximize()

		if fullscreen:
			window.fullscreen()
		else:
			window.unfullscreen()


	# side panel page name

	def save_side_panel_page_name(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		side_panel = window.get_side_panel()
		page_name = side_panel.get_visible_child_name()
		if not page_name:
			page_name = ''

		if page_name == self.side_panel_page_name:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("saving page_name=%s", page_name))

		self.side_panel_page_name = page_name

		return True

	def apply_side_panel_page_name(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		page_name = self.side_panel_page_name

		if not page_name:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("no page name"))

			return

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("applying page_name=%s", page_name))

		side_panel = window.get_side_panel()
		side_panel.set_visible_child_name(page_name)


	# side panel visible

	def save_side_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		side_panel = window.get_side_panel()
		visible = side_panel.get_visible()

		if visible == self.side_panel_visible:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("saving visible=%s", visible))

		self.side_panel_visible = visible

		return True

	def apply_side_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		visible = self.side_panel_visible

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("applying visible=%s", visible))

		side_panel = window.get_side_panel()
		side_panel.set_visible(visible)


	# bottom panel page name

	def save_bottom_panel_page_name(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		bottom_panel = window.get_bottom_panel()
		page_name = bottom_panel.get_visible_child_name()
		if not page_name:
			page_name = ''

		if page_name == self.bottom_panel_page_name:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("saving page_name=%s", page_name))

		self.bottom_panel_page_name = page_name

		return True

	def apply_bottom_panel_page_name(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		page_name = self.bottom_panel_page_name

		if not page_name:
			# it is possible there is no bottom panel
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no page name"))

			return

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("applying page_name=%s", page_name))

		bottom_panel = window.get_bottom_panel()
		bottom_panel.set_visible_child_name(page_name)


	# bottom panel visible

	def save_bottom_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		bottom_panel = window.get_bottom_panel()
		visible = bottom_panel.get_visible()

		if visible == self.bottom_panel_visible:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("saving visible=%s", visible))

		self.bottom_panel_visible = visible

		return True

	def apply_bottom_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		visible = self.bottom_panel_visible

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("applying visible=%s", visible))

		bottom_panel = window.get_bottom_panel()
		bottom_panel.set_visible(visible)


	# hpaned position

	def save_hpaned_position(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		hpaned = window.get_template_child(Gedit.Window, 'hpaned')
		position = hpaned.get_position()

		if position == self.hpaned_position:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("saving position=%s", position))

		self.hpaned_position = position

		return True

	def apply_hpaned_position(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		position = self.hpaned_position

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("applying position=%s", position))

		hpaned = window.get_template_child(Gedit.Window, 'hpaned')
		hpaned.set_position(position)


	# vpaned position

	def save_vpaned_position(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		vpaned = window.get_template_child(Gedit.Window, 'vpaned')
		position = vpaned.get_position()

		if position == self.vpaned_position:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("saving position=%s", position))

		self.vpaned_position = position

		return True

	def apply_vpaned_position(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		position = self.vpaned_position

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("applying position=%s", position))

		vpaned = window.get_template_child(Gedit.Window, 'vpaned')
		vpaned.set_position(position)


def copy_uris(source):
	return [[uri for uri in uris] for uris in source]

def copy_tab_map(source):
	return {tab : indices for tab, indices in source.items()}

def get_tab_uri(tab):
	source_file = tab.get_document().get_file()
	location = source_file.get_location() if source_file else None
	uri = location.get_uri() if location else None
	return uri

