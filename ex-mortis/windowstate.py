# -*- coding: utf-8 -*-
#
# windowstate.py
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
gi.require_version('Gdk', '3.0')
gi.require_version('Gedit', '3.0')
gi.require_version('Gio', '2.0')
gi.require_version('Gtk', '3.0')

from gi.repository import GObject, Gdk, Gedit, Gio, Gtk
from . import log


class ExMortisWindowState(GObject.Object):

	__gtype_name__ = 'ExMortisWindowState'

	active_uri = GObject.Property(type=str, default='')

	width = GObject.Property(type=int, default=0)

	height = GObject.Property(type=int, default=0)

	maximized = GObject.Property(type=bool, default=False)

	fullscreen = GObject.Property(type=bool, default=False)

	side_panel_page_name = GObject.Property(type=str, default='')

	side_panel_size = GObject.Property(type=int, default=0)

	side_panel_visible = GObject.Property(type=bool, default=False)

	bottom_panel_page_name = GObject.Property(type=str, default='')

	bottom_panel_size = GObject.Property(type=int, default=0)

	bottom_panel_visible = GObject.Property(type=bool, default=False)


	def __init__(self):
		GObject.Object.__init__(self)

		self._notebook_map = {}
		self._tab_map = {}
		self._restore_filter = []
		self._uris = []
		self._restore_uris = []
		self._notebook_widths = []
		self._restore_notebook_widths = []
		self._active_tab = None


	# class methods

	@classmethod
	def clone(cls, source):
		clone = cls()

		try:
			params = cls.list_properties()
		except AttributeError: # gedit 3.12
			params = GObject.list_properties(cls)

		for param in params:
			clone.set_property(param.name, source.get_property(param.name))

		clone._notebook_map = dict(source._notebook_map)
		clone._tab_map = dict(source._tab_map)
		clone._active_tab = source._active_tab

		clone.uris = source.uris
		clone.notebook_widths = source.notebook_widths

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
	def notebook_widths(self):
		return list(self._notebook_widths)

	@notebook_widths.setter
	def notebook_widths(self, value):
		notebook_widths = list(value)

		if notebook_widths != self._notebook_widths:
			self._notebook_widths = notebook_widths

			self.emit('notebook-widths-changed')

	@property
	def restore_notebook_widths(self):
		return list(self._restore_notebook_widths)


	# signals

	@GObject.Signal
	def uris_changed(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		filtered = [[uri for uri in uris if uri] for uris in self._uris]

		self._restore_uris = [uris for uris in filtered if uris]

		restore_filter = [bool(uris) for uris in filtered]

		if restore_filter != self._restore_filter:
			self._restore_filter = restore_filter

			self.emit('notebook-widths-changed')

	@GObject.Signal
	def notebook_widths_changed(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		zipped = zip(self._restore_filter, self._notebook_widths)
		self._restore_notebook_widths = [width for can_restore, width in zipped if can_restore]


	# saving / applying windows

	def save_window(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		self.update_structure(window)
		self.save_active_uri(window, window.get_active_tab())

		# window state affects whether size is saved or not
		self.save_window_state(window)
		self.save_size(window)

		self.save_side_panel_page_name(window)
		self.save_side_panel_visible(window)
		self.save_bottom_panel_page_name(window)
		self.save_bottom_panel_visible(window)

		self.save_side_panel_size(window)
		self.save_bottom_panel_size(window)

	def apply_window(self, window, is_new_window=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, is_new_window=%s", window, is_new_window))

		# need to unmaximize/unfullscreen to set size
		window.unmaximize()
		window.unfullscreen()

		self.apply_size(window, is_new_window)
		self.apply_window_state(window)

		self.apply_side_panel_page_name(window)
		self.apply_side_panel_visible(window)
		self.apply_bottom_panel_page_name(window)
		self.apply_bottom_panel_visible(window)

		if is_new_window:
			window.show()

		self.apply_side_panel_size(window)
		self.apply_bottom_panel_size(window)

		self.apply_uris(window)
		self.apply_active_uri(window)

		self.apply_notebook_widths(window)


	# property helpers

	def save_property(self, property_name, value):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s=%s", property_name, value))

		prev = self.get_property(property_name)

		if value == prev:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("prev %s=%s", property_name, prev))

		self.set_property(property_name, value)

		return True


	# window structure

	def update_structure(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		prev_uris = self._uris
		prev_notebook_widths = self._notebook_widths

		notebook_map = {}
		tab_map = {}
		uris = []
		notebook_widths = []

		for document in window.get_documents():
			tab = Gedit.Tab.get_from_document(document)
			notebook = tab.get_parent()

			if notebook not in notebook_map:
				notebook_map[notebook] = len(uris)
				uris.append([])
				notebook_widths.append(0)

			notebook_index = notebook_map[notebook]
			notebook_uris = uris[notebook_index]

			tab_index = len(notebook_uris)
			notebook_uris.append('')

			tab_map[tab] = (notebook_index, tab_index)

		self._notebook_map = notebook_map
		self._tab_map = tab_map
		self._uris = uris
		self._notebook_widths = notebook_widths

		self.save_uris(window, True)
		self.save_notebook_widths(window, True)

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("uris=%s, notebook_widths=%s", uris, notebook_widths))

		if uris == prev_uris and notebook_widths == prev_notebook_widths:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if uris != prev_uris:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("prev uris=%s", prev_uris))

			self.emit('uris-changed')

		if notebook_widths != prev_notebook_widths:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("prev notebook_widths=%s", prev_notebook_widths))

			self.emit('notebook-widths-changed')

		return True

	def forget_notebooks(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		self._notebook_map = {}

	def forget_notebook(self, notebook):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", notebook))

		if notebook in self._notebook_map:
			del self._notebook_map[notebook]

	def forget_tabs(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		self._tab_map = {}
		self._active_tab = None

	def forget_tab(self, tab):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", tab))

		if tab is self._active_tab:
			self._active_tab = None

		if tab in self._tab_map:
			del self._tab_map[tab]


	# window uris

	def save_uris(self, window, bulk_update=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, bulk_update=%s", window, bulk_update))

		results = [self.save_uri(window, tab, True) for tab in self._tab_map.keys()]
		changed = any(results)

		if not bulk_update and changed:
			self.emit('uris-changed')

		return changed

	def save_uri(self, window, tab, bulk_update=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s, bulk_update=%s", window, tab, bulk_update))

		if not bulk_update and tab is self._active_tab:
			self.save_active_uri(window)

		if tab not in self._tab_map:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("not in tab map"))

			return False

		notebook_index, tab_index = self._tab_map[tab]

		prev_uri = self._uris[notebook_index][tab_index]

		uri = get_tab_uri(tab)

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("uri=%s", uri))

		if uri == prev_uri:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("prev uri=%s", prev_uri))

		self._uris[notebook_index][tab_index] = uri

		if not bulk_update:
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


	# window notebook widths

	def save_notebook_widths(self, window, bulk_update=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, bulk_update=%s", window, bulk_update))

		results = [self.save_notebook_width(window, notebook, True) for notebook in self._notebook_map.keys()]
		changed = any(results)

		if not bulk_update and changed:
			self.emit('notebook-widths-changed')

		return changed

	def save_notebook_width(self, window, notebook, bulk_update=False):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s, %s, bulk_update=%s", window, notebook, bulk_update))

		if notebook not in self._notebook_map:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("not in notebook map"))

			return False

		notebook_index = self._notebook_map[notebook]

		prev_notebook_width = self._notebook_widths[notebook_index]

		notebook_width = notebook.get_allocation().width

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("notebook_width=%s", notebook_width))

		if notebook_width == prev_notebook_width:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no change"))

			return False

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("prev notebook_width=%s", prev_notebook_width))

		self._notebook_widths[notebook_index] = notebook_width

		if not bulk_update:
			self.emit('notebook-widths-changed')

		return True

	def apply_notebook_widths(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		# this only works with the notebook structure created by apply_uris()

		notebook_widths = list(self._notebook_widths)
		notebooks = []
		notebooks_set = set()

		if len(notebook_widths) < 2:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("have %s notebook widths, not enough to apply", len(notebook_widths)))

			return

		for document in window.get_documents():
			notebook = Gedit.Tab.get_from_document(document).get_parent()

			if notebook not in notebooks_set:
				notebooks.append(notebook)
				notebooks_set.add(notebook)

		if len(notebooks) < 2:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("have %s notebooks, not enough to apply", len(notebooks)))

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("applying notebook_widths=%s", notebook_widths))

		min_len = min(len(notebooks), len(notebook_widths))

		# we won't set the width of the last notebook
		zipped = zip(notebooks[-min_len:-1], notebook_widths[-min_len:-1])

		for notebook, notebook_width in zipped:
			parent = notebook.get_parent()

			if not isinstance(parent, Gtk.Paned):
				if log.query(log.DEBUG):
					Gedit.debug_plugin_message(log.format("parent %s of notebook %s is not a Gtk.Paned", parent, notebook))

				continue

			if parent.get_child2() is notebook:
				if log.query(log.DEBUG):
					Gedit.debug_plugin_message(log.format("notebook %s is not the left child of parent %s", notebook, parent))

				continue

			parent.set_position(notebook_width)


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

		# gedit should (always?) set a default size
		# if it hasn't been set on this window yet,
		# get_size() will return a wrong size

		default_width, default_height = window.get_default_size()

		if default_width == -1 and default_height == -1:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("default size not set"))

			return False

		width = 0
		height = 0

		if not self.maximized and not self.fullscreen:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("using get_size()"))

			width, height = window.get_size()

		# if we haven't saved before, try default size
		elif not self.width and not self.height:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("using get_default_size()"))

			width = default_width
			height = default_height

		if not width or not height:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("no size to save"))

			return False

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

		try:
			page_name = side_panel.get_active_item_name()
		except AttributeError: # gedit 45
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
		try:
			side_panel.set_active_item_name(page_name)
		except AttributeError: # gedit 45
			side_panel.set_visible_child_name(page_name)


	# side panel size

	def save_side_panel_size(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		hpaned = window.get_template_child(Gedit.Window, 'hpaned')
		position = hpaned.get_position()

		return self.save_property('side-panel-size', position)

	def apply_side_panel_size(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		size = self.side_panel_size

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("applying size=%s", size))

		hpaned = window.get_template_child(Gedit.Window, 'hpaned')
		hpaned.set_position(size)


	# side panel visible

	def save_side_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		side_panel = window.get_template_child(Gedit.Window, 'side_panel')
		visible = side_panel.get_visible()

		return self.save_property('side-panel-visible', visible)

	def apply_side_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		visible = self.side_panel_visible

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("applying visible=%s", visible))

		side_panel = window.get_template_child(Gedit.Window, 'side_panel')
		side_panel.set_visible(visible)


	# bottom panel page name

	def save_bottom_panel_page_name(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		bottom_panel = window.get_bottom_panel()

		try:
			page_name = bottom_panel.get_active_item_name()
		except AttributeError: # gedit 47
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
		try:
			bottom_panel.set_active_item_name(page_name)
		except AttributeError: # gedit 47
			bottom_panel.set_visible_child_name(page_name)


	# bottom panel size

	def save_bottom_panel_size(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		vpaned = window.get_template_child(Gedit.Window, 'vpaned')
		height = vpaned.get_allocation().height
		position = vpaned.get_position()
		size = max(height - position, 50)

		return self.save_property('bottom-panel-size', size)

	def apply_bottom_panel_size(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		size = self.bottom_panel_size

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("applying size=%s", size))

		vpaned = window.get_template_child(Gedit.Window, 'vpaned')
		height = vpaned.get_allocation().height
		position = max(height - size, 50)
		vpaned.set_position(position)


	# bottom panel visible

	def save_bottom_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		bottom_panel = window.get_template_child(Gedit.Window, 'bottom_panel')
		visible = bottom_panel.get_visible()

		return self.save_property('bottom-panel-visible', visible)

	def apply_bottom_panel_visible(self, window):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window))

		visible = self.bottom_panel_visible

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("applying visible=%s", visible))

		bottom_panel = window.get_template_child(Gedit.Window, 'bottom_panel')
		bottom_panel.set_visible(visible)


def copy_uris(source):
	return [[uri for uri in uris] for uris in source]

def get_tab_uri(tab):
	document = tab.get_document()
	try:
		location = document.get_file().get_location()
	except AttributeError: # gedit 3.12
		location = document.get_location()
	return location.get_uri() if location else ''

