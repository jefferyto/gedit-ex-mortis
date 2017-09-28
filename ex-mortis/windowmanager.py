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


class ExMortisWindowManager(GObject.Object):

	__gtype_name__ = 'ExMortisWindowManager'


	def __init__(self):
		GObject.Object.__init__(self)

		Gedit.debug_plugin_message("")

		self._windows = {}
		self._save_size_ids = {}

	def cleanup(self):
		Gedit.debug_plugin_message("")

		windows = self._windows.keys()

		for window in windows:
			self.untrack_window(window)

		self._windows = None
		self._save_size_ids = None


	# signals

	@GObject.Signal(arg_types=(Gedit.Window, Gedit.Tab))
	def tab_added(self, window, tab):
		Gedit.debug_plugin_message("%s, %s", debug_str(window), debug_str(tab))

	@GObject.Signal(arg_types=(Gedit.Window, Gedit.Tab))
	def tab_removed(self, window, tab):
		Gedit.debug_plugin_message("%s, %s", debug_str(window), debug_str(tab))

	@GObject.Signal(arg_types=(Gedit.Window,))
	def tabs_reordered(self, window):
		Gedit.debug_plugin_message("%s", debug_str(window))

	@GObject.Signal(arg_types=(Gedit.Window, Gedit.Tab))
	def tab_updated(self, window, tab):
		Gedit.debug_plugin_message("%s, %s", debug_str(window), debug_str(tab))


	# tracking / untracking windows

	def track_window(self, window):
		Gedit.debug_plugin_message("%s", debug_str(window))

		if window in self._windows:
			Gedit.debug_plugin_message("window already being tracked")
			return

		state = ExMortisWindowState()
		side_panel = window.get_side_panel()
		bottom_panel = window.get_bottom_panel()

		connect_handlers(
			self, window,
			[
				'tab-added',
				'tab-removed',
				'tabs-reordered',
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

		self._windows[window] = state

		for document in window.get_documents():
			self.track_tab(window, Gedit.Tab.get_from_document(document), state)

	def untrack_window(self, window):
		Gedit.debug_plugin_message("%s", debug_str(window))

		if window not in self._windows:
			Gedit.debug_plugin_message("unknown window")
			return

		if window in self._save_size_ids:
			GLib.source_remove(self._save_size_ids[window])
			del self._save_size_ids[window]

		state = self._windows[window]
		side_panel = window.get_side_panel()
		bottom_panel = window.get_bottom_panel()

		disconnect_handlers(self, window)
		disconnect_handlers(self, side_panel)
		disconnect_handlers(self, bottom_panel)

		for document in window.get_documents():
			self.untrack_tab(window, Gedit.Tab.get_from_document(document), state)

		del self._windows[window]

	def track_tab(self, window, tab, state):
		Gedit.debug_plugin_message("%s, %s", debug_str(window), debug_str(tab))

		connect_handlers(self, tab, ['notify::name'], 'tab', window, state)

	def untrack_tab(self, window, tab, state):
		Gedit.debug_plugin_message("%s, %s", debug_str(window), debug_str(tab))

		disconnect_handlers(self, tab)


	# window state

	def new_window_state(self):
		Gedit.debug_plugin_message("")

		return ExMortisWindowState()

	def get_window_state(self, window):
		Gedit.debug_plugin_message("%s", debug_str(window))

		if window not in self._windows:
			Gedit.debug_plugin_message("unknown window")
			return None

		return self._windows[window]

	def export_window_state(self, window):
		Gedit.debug_plugin_message("%s", debug_str(window))

		if window not in self._windows:
			Gedit.debug_plugin_message("unknown window")
			return None

		return ExMortisWindowState.clone(self._windows[window])

	def import_window_state(self, window, state, set_default_size=False):
		Gedit.debug_plugin_message("%s, set_default_size=%s", debug_str(window), set_default_size)

		if window not in self._windows:
			Gedit.debug_plugin_message("unknown window")
			return

		state.apply_size(window, set_default_size)

		window.show()

		state.apply_window(window, True)

	def save_to_window_state(self, window):
		Gedit.debug_plugin_message("%s", debug_str(window))

		if window not in self._windows:
			Gedit.debug_plugin_message("unknown window")
			return

		state = self._windows[window]
		state.save_window(window)

	def restore_from_window_state(self, window):
		Gedit.debug_plugin_message("%s", debug_str(window))

		if window not in self._windows:
			Gedit.debug_plugin_message("unknown window")
			return

		state = self._windows[window]
		state.apply_window(window)

	def open_new_window_with_window_state(self, state):
		Gedit.debug_plugin_message("")

		app = Gedit.App.get_default()
		window = Gedit.App.create_window(app, None)

		self.import_window_state(window, state, True)

		window.present()


	# signal handlers

	def on_window_tab_added(self, window, tab, state):
		Gedit.debug_plugin_message("%s, %s", debug_str(window), debug_str(tab))

		self.track_tab(window, tab, state)

		state.save_uris(window)

		self.emit('tab-added', window, tab)

	def on_window_tab_removed(self, window, tab, state):
		Gedit.debug_plugin_message("%s, %s", debug_str(window), debug_str(tab))

		self.untrack_tab(window, tab, state)

		state.save_uris(window)

		self.emit('tab-removed', window, tab)

	def on_window_tabs_reordered(self, window, state):
		Gedit.debug_plugin_message("%s", debug_str(window))

		state.save_uris(window)

		self.emit('tabs-reordered', window)

	def on_tab_notify_name(self, tab, pspec, window, state):
		Gedit.debug_plugin_message("%s, %s", debug_str(window), debug_str(tab))

		state.update_uri_from_tab(tab)

		self.emit('tab-updated', window, tab)

	def on_window_size_allocate(self, window, allocation, state):
		#Gedit.debug_plugin_message("%s", debug_str(window))

		# because this signal is emitted way too frequently
		if window in self._save_size_ids:
			GLib.source_remove(self._save_size_ids[window])

		self._save_size_ids[window] = GLib.timeout_add(
			1000, self.on_timeout_save_window_size, window, state
		)

	def on_window_window_state_event(self, window, event, state):
		Gedit.debug_plugin_message("%s", debug_str(window))

		state.save_window_state(window, event.new_window_state)

	def on_side_panel_notify_visible_child_name(self, side_panel, pspec, window, state):
		Gedit.debug_plugin_message("%s", debug_str(window))

		state.save_side_panel_page_name(window)

	def on_side_panel_notify_visible(self, side_panel, pspec, window, state):
		Gedit.debug_plugin_message("%s", debug_str(window))

		state.save_side_panel_visible(window)

	def on_bottom_panel_notify_visible_child_name(self, bottom_panel, pspec, window, state):
		Gedit.debug_plugin_message("%s", debug_str(window))

		state.save_bottom_panel_page_name(window)

	def on_bottom_panel_notify_visible(self, bottom_panel, pspec, window, state):
		Gedit.debug_plugin_message("%s", debug_str(window))

		state.save_bottom_panel_visible(window)

	def on_timeout_save_window_size(self, window, state):
		Gedit.debug_plugin_message("%s", debug_str(window))

		if not state.maximized and not state.fullscreen:
			state.save_size(window)

		if window in self._save_size_ids:
			del self._save_size_ids[window]

		return False


class ExMortisWindowState(GObject.Object):

	__gtype_name__ = 'ExMortisWindowState'

	width = GObject.Property(type=int, default=0)

	height = GObject.Property(type=int, default=0)

	maximized = GObject.Property(type=bool, default=False)

	fullscreen = GObject.Property(type=bool, default=False)

	side_panel_page_name = GObject.Property(type=str, default='')

	side_panel_visible = GObject.Property(type=bool, default=False)

	bottom_panel_page_name = GObject.Property(type=str, default='')

	bottom_panel_visible = GObject.Property(type=bool, default=False)


	def __init__(self):
		GObject.Object.__init__(self)

		self._uris = []
		self._filtered_uris = []
		self._tab_map = {}


	# class methods

	@classmethod
	def clone(cls, source):
		clone = cls()

		for param in cls.list_properties():
			clone.set_property(param.name, source.get_property(param.name))

		clone.uris = source.uris
		clone.tab_map = source.tab_map

		return clone


	# properties

	@property
	def uris(self):
		return copy_uris(self._uris)

	@uris.setter
	def uris(self, value):
		prev_uris = self._uris
		uris = copy_uris(value)

		if uris != prev_uris:
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
		Gedit.debug_plugin_message("")

		filtered = [[uri for uri in uris if uri] for uris in self._uris]
		self._filtered_uris = [uris for uris in filtered if uris]


	# saving / applying windows

	def save_window(self, window):
		Gedit.debug_plugin_message("%s", debug_str(window))

		self.save_uris(window, True)
		self.save_size(window)
		self.save_window_state(window)
		self.save_side_panel_page_name(window)
		self.save_side_panel_visible(window)
		self.save_bottom_panel_page_name(window)
		self.save_bottom_panel_visible(window)

	def apply_window(self, window, skip_size=False):
		Gedit.debug_plugin_message("%s, skip_size=%s", debug_str(window), skip_size)

		self.apply_uris(window)
		if not skip_size:
			self.apply_size(window)
		self.apply_window_state(window)
		self.apply_side_panel_page_name(window)
		self.apply_side_panel_visible(window)
		self.apply_bottom_panel_page_name(window)
		self.apply_bottom_panel_visible(window)


	# window uris

	def save_uris(self, window, force_save=False):
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

		Gedit.debug_plugin_message("%s, force_save=%s, saving uris=%s", debug_str(window), force_save, uris)

		prev_uris = self._uris

		self._tab_map = tab_map

		if force_save or uris != prev_uris:
			self._uris = uris

			self.emit('uris-changed')

	def update_uri_from_tab(self, tab, forget_tab=False):
		Gedit.debug_plugin_message("%s, forget_tab=%s", debug_str(tab), forget_tab)

		if tab not in self._tab_map:
			Gedit.debug_plugin_message("tab not in tab map")
			return

		notebook_index, tab_index = self._tab_map[tab]

		prev_uri = self._uris[notebook_index][tab_index]
		uri = get_tab_uri(tab)

		if forget_tab:
			del self._tab_map[tab]

		if uri != prev_uri:
			self._uris[notebook_index][tab_index] = uri

			self.emit('uris-changed')

	def apply_uris(self, window):
		uris = self._filtered_uris

		Gedit.debug_plugin_message("%s, applying uris=%s", debug_str(window), uris)

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


	# window size

	def save_size(self, window):
		width, height = window.get_size()

		Gedit.debug_plugin_message("%s, saving width=%s, height=%s", debug_str(window), width, height)

		self.width = width
		self.height = height

	def apply_size(self, window, set_default_size=False):
		width = self.width
		height = self.height

		Gedit.debug_plugin_message("%s, set_default_size=%s, applying width=%s, height=%s", debug_str(window), set_default_size, width, height)

		if set_default_size:
			window.set_default_size(width, height)
		else:
			window.resize(width, height)


	# window state (maximized / fullscreen)

	def save_window_state(self, window, window_state=None):
		if window_state is None:
			Gedit.debug_plugin_message("%s, getting window state from window", debug_str(window))

			gdk_window = window.get_window()

			if not gdk_window:
				Gedit.debug_plugin_message("window not yet realized")
				return

			window_state = gdk_window.get_state()

		maximized = (window_state & Gdk.WindowState.MAXIMIZED) != 0
		fullscreen = (window_state & Gdk.WindowState.FULLSCREEN) != 0

		Gedit.debug_plugin_message("%s, saving maximized=%s, fullscreen=%s", debug_str(window), maximized, fullscreen)

		self.maximized = maximized
		self.fullscreen = fullscreen

	def apply_window_state(self, window):
		maximized = self.maximized
		fullscreen = self.fullscreen

		Gedit.debug_plugin_message("%s, applying maximized=%s, fullscreen=%s", debug_str(window), maximized, fullscreen)

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
		side_panel = window.get_side_panel()
		page_name = side_panel.get_visible_child_name()

		Gedit.debug_plugin_message("%s, saving page_name=%s", debug_str(window), page_name)

		self.side_panel_page_name = page_name if page_name else ''

	def apply_side_panel_page_name(self, window):
		page_name = self.side_panel_page_name

		if not page_name:
			Gedit.debug_plugin_message("%s, no page name", debug_str(window))
			return

		Gedit.debug_plugin_message("%s, applying page_name=%s", debug_str(window), page_name)

		side_panel = window.get_side_panel()
		side_panel.set_visible_child_name(page_name)


	# side panel visible

	def save_side_panel_visible(self, window):
		side_panel = window.get_side_panel()
		visible = side_panel.get_visible()

		Gedit.debug_plugin_message("%s, saving visible=%s", debug_str(window), visible)

		self.side_panel_visible = visible

	def apply_side_panel_visible(self, window):
		visible = self.side_panel_visible

		Gedit.debug_plugin_message("%s, applying visible=%s", debug_str(window), visible)

		side_panel = window.get_side_panel()
		side_panel.set_visible(visible)


	# bottom panel page name

	def save_bottom_panel_page_name(self, window):
		bottom_panel = window.get_bottom_panel()
		page_name = bottom_panel.get_visible_child_name()

		Gedit.debug_plugin_message("%s, saving page_name=%s", debug_str(window), page_name)

		self.bottom_panel_page_name = page_name if page_name else ''

	def apply_bottom_panel_page_name(self, window):
		page_name = self.bottom_panel_page_name

		if not page_name:
			Gedit.debug_plugin_message("%s, no page name", debug_str(window))
			return

		Gedit.debug_plugin_message("%s, applying page_name=%s", debug_str(window), page_name)

		bottom_panel = window.get_bottom_panel()
		bottom_panel.set_visible_child_name(page_name)


	# bottom panel visible

	def save_bottom_panel_visible(self, window):
		bottom_panel = window.get_bottom_panel()
		visible = bottom_panel.get_visible()

		Gedit.debug_plugin_message("%s, saving visible=%s", debug_str(window), visible)

		self.bottom_panel_visible = visible

	def apply_bottom_panel_visible(self, window):
		visible = self.bottom_panel_visible

		Gedit.debug_plugin_message("%s, applying visible=%s", debug_str(window), visible)

		bottom_panel = window.get_bottom_panel()
		bottom_panel.set_visible(visible)


def copy_uris(source):
	return [[uri for uri in uris] for uris in source]

def copy_tab_map(source):
	return {tab : indices for tab, indices in source.items()}

def get_tab_uri(tab):
	source_file = tab.get_document().get_file()
	location = source_file.get_location() if source_file else None
	uri = location.get_uri() if location else None
	return uri

