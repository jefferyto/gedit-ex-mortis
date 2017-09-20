# -*- coding: utf-8 -*-
#
# window_info.py
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

from gi.repository import Gio, Gedit


def get_info(window):
	window_uris = []
	notebook_map = {}
	# don't map document objects because document objects are transient
	# whereas tab objects are more permanent?
	tab_map = {}

	for document in window.get_documents():
		tab = Gedit.Tab.get_from_document(document)
		notebook = tab.get_parent()

		if notebook not in notebook_map:
			notebook_map[notebook] = len(window_uris)
			window_uris.append([])

		notebook_index = notebook_map[notebook]
		notebook_uris = window_uris[notebook_index]

		tab_index = len(notebook_uris)
		notebook_uris.append(get_document_uri(document))

		tab_map[hash(tab)] = (notebook_index, tab_index)

	return (window_uris, tab_map)

def update_info(window_uris, tab_map, tab):
	tab_hash = hash(tab)

	if tab_hash in tab_map:
		notebook_index, tab_index = tab_map[tab_hash]
		window_uris[notebook_index][tab_index] = get_document_uri(tab.get_document())

	else:
		Gedit.debug_plugin_message("tab id not in tab map?")

def filter_uris(window_uris, tab_map=None):
	window_uris = [
		[uri for uri in notebook_uris if uri]
		for notebook_uris in window_uris
	]

	return [
		notebook_uris
		for notebook_uris in window_uris
		if notebook_uris
	]

def open_uris_in_window(window_uris, window=None):
	window_uris = filter_uris(window_uris)

	if window_uris:
		if not window:
			app = Gedit.App.get_default()
			window = Gedit.App.create_window(app, None)

		window.show()

		is_first_notebook = True

		for notebook_uris in window_uris:
			if not is_first_notebook:
				window.activate_action('new-tab-group')

			locations = [
				Gio.File.new_for_uri(uri)
				for uri in notebook_uris
			]

			Gedit.commands_load_locations(window, locations, None, 0, 0)

			is_first_notebook = False

		window.present()

def get_document_uri(document):
	source_file = document.get_file()
	location = source_file.get_location() if source_file else None
	uri = location.get_uri() if location else None
	return uri
