# -*- coding: utf-8 -*-
#
# windowstate.py
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

from gi.repository import GObject, Gdk, Gio, Gedit
from .utils import connect_handlers, disconnect_handlers
from . import log


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
		self._restore_uris = []
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
	def restore_uris(self):
		return copy_uris(self._restore_uris)

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

		restore = [[uri for uri in uris if uri] for uris in self._uris]
		self._restore_uris = [uris for uris in restore if uris]


	# saving / applying windows

	def save_window(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		self.save_uris(window)
		self.save_active_uri(window, window.get_active_tab())
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


	# property helpers

	def save_property(self, property_name, value):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s=%s", property_name, value))

		prev = self.get_property(property_name)

		if value != prev:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("prev %s=%s", property_name, prev))

		self.set_property(property_name, value)

		return True


	# window uris

	def save_uris(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		prev_uris = self._uris

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

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("uris=%s", uris))

		if uris == prev_uris:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("prev uris=%s", prev_uris))

		self._uris = uris

		self.emit('uris-changed')

		return True

	def update_uri_from_tab(self, window, tab, forget_tab=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s, forget_tab=%s", window, tab, forget_tab))

		# active uri

		if tab is self._active_tab:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("active tab"))

			self.save_active_uri(window)

			if forget_tab:
				self._active_tab = None

		else:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("not active tab"))

		# uris

		if tab not in self._tab_map:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("not in tab map"))

			return False

		notebook_index, tab_index = self._tab_map[tab]

		prev_uri = self._uris[notebook_index][tab_index]

		uri = get_tab_uri(tab)

		if forget_tab:
			del self._tab_map[tab]

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("uri=%s", uri))

		if uri == prev_uri:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("prev uri=%s", prev_uri))

		self._uris[notebook_index][tab_index] = uri

		self.emit('uris-changed')

		return True

	def apply_uris(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		uris = self._restore_uris

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("applying uris=%s", uris))

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

	def save_active_uri(self, window, new_active_tab=None):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s", window, new_active_tab))

		if new_active_tab:
			self._active_tab = new_active_tab

		active_tab = self._active_tab

		if not active_tab:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no active tab"))

			return False

		active_uri = get_tab_uri(active_tab)

		return self.save_property('active-uri', active_uri)

	def apply_active_uri(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		active_uri = self.active_uri

		if not active_uri:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no active uri"))

			return

		if log.query(log.DEBUG):
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

		results = [
			self.save_property('width', width),
			self.save_property('height', height)
		]

		return any(results)

	def apply_size(self, window, set_default_size=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, set_default_size=%s", window, set_default_size))

		width = self.width
		height = self.height

		if log.query(log.DEBUG):
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
				if log.query(log.DEBUG):
					Gedit.debug_plugin_message(log.format("window not yet realized"))

				return False

			window_state = gdk_window.get_state()

		maximized = bool(window_state & Gdk.WindowState.MAXIMIZED)
		fullscreen = bool(window_state & Gdk.WindowState.FULLSCREEN)

		results = [
			self.save_property('maximized', maximized),
			self.save_property('fullscreen', fullscreen)
		]

		return any(results)

	def apply_window_state(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		maximized = self.maximized
		fullscreen = self.fullscreen

		if log.query(log.DEBUG):
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

		return self.save_property('side-panel-page-name', page_name)

	def apply_side_panel_page_name(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		page_name = self.side_panel_page_name

		if not page_name:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("no page name"))

			return

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("applying page_name=%s", page_name))

		side_panel = window.get_side_panel()
		side_panel.set_visible_child_name(page_name)


	# side panel visible

	def save_side_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		side_panel = window.get_side_panel()
		visible = side_panel.get_visible()

		return self.save_property('side-panel-visible', visible)

	def apply_side_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		visible = self.side_panel_visible

		if log.query(log.DEBUG):
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

		return self.save_property('bottom-panel-page-name', page_name)

	def apply_bottom_panel_page_name(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		page_name = self.bottom_panel_page_name

		if not page_name:
			# it is possible there are no bottom panel pages
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no page name"))

			return

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("applying page_name=%s", page_name))

		bottom_panel = window.get_bottom_panel()
		bottom_panel.set_visible_child_name(page_name)


	# bottom panel visible

	def save_bottom_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		bottom_panel = window.get_bottom_panel()
		visible = bottom_panel.get_visible()

		return self.save_property('bottom-panel-visible', visible)

	def apply_bottom_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		visible = self.bottom_panel_visible

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("applying visible=%s", visible))

		bottom_panel = window.get_bottom_panel()
		bottom_panel.set_visible(visible)


	# hpaned position

	def save_hpaned_position(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		hpaned = window.get_template_child(Gedit.Window, 'hpaned')
		position = hpaned.get_position()

		return self.save_property('hpaned-position', position)

	def apply_hpaned_position(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		position = self.hpaned_position

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("applying position=%s", position))

		hpaned = window.get_template_child(Gedit.Window, 'hpaned')
		hpaned.set_position(position)


	# vpaned position

	def save_vpaned_position(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		vpaned = window.get_template_child(Gedit.Window, 'vpaned')
		position = vpaned.get_position()

		return self.save_property('vpaned-position', position)

	def apply_vpaned_position(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		position = self.vpaned_position

		if log.query(log.DEBUG):
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

