# -*- coding: utf-8 -*-
#
# settings.py
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

import os.path
from gi.repository import GObject, Gio, Gedit
from .plugin import data_dir as plugin_data_dir
from . import log


class ExMortisSettings(GObject.Object):

	__gtype_name__ = 'ExMortisSettings'

	restore_between_sessions = GObject.Property(type=bool, default=False)

	restore_windows = GObject.Property(type=GObject.GType.from_name('GStrv'), default=[])


	def __init__(self, is_enabled=True):
		GObject.Object.__init__(self)

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("is_enabled=%s", is_enabled))

		schemas_path = os.path.join(plugin_data_dir, 'schemas')

		try:
			schema_source = Gio.SettingsSchemaSource.new_from_directory(
				schemas_path,
				Gio.SettingsSchemaSource.get_default(),
				False
			)

		except:
			if log.query(log.CRITICAL):
				Gedit.debug_plugin_message(log.format("could not load settings schema source from %s", schemas_path))

			schema_source = None

		if is_enabled:
			settings = get_settings(
				schema_source,
				'com.thingsthemselves.gedit.plugins.ex-mortis',
				'/com/thingsthemselves/gedit/plugins/ex-mortis/'
			)
		else:
			settings = None

		if settings:
			try:
				params = self.list_properties()
			except AttributeError: # gedit 3.12
				params = GObject.list_properties(self)

			for param in params:
				settings.bind(
					param.name,
					self, param.name,
					Gio.SettingsBindFlags.DEFAULT
				)

		self._schema_source = schema_source
		self._settings = settings
		self._window_settings = {}

		for window_id in self.restore_windows:
			self.init_window_settings(window_id)

	def cleanup(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		settings = self._settings

		if settings:
			try:
				params = self.list_properties()
			except AttributeError: # gedit 3.12
				params = GObject.list_properties(self)

			for param in params:
				try:
					settings.unbind(self, param.name)
				except ValueError: # gedit 3.14
					pass

		self._schema_source = None
		self._settings = None
		self._window_settings = None


	@property
	def can_save(self):
		return bool(self._settings)


	def add_window(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		window_id = self.find_unused_window_id()

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("adding window_id=%s", window_id))

		self.init_window_settings(window_id)

		restore_windows = self.restore_windows
		restore_windows.append(window_id)
		self.restore_windows = restore_windows

		return window_id

	def remove_window(self, window_id):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("window_id=%s", window_id))

		if window_id not in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("unknown window id"))

			return

		self.reset_window_settings(window_id)

		restore_windows = self.restore_windows
		restore_windows.remove(window_id)
		self.restore_windows = restore_windows

		del self._window_settings[window_id]

	def find_unused_window_id(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format(""))

		window_id_set = set(self.restore_windows)
		counter = 0

		while True:
			window_id = 'window' + str(counter)

			if window_id not in window_id_set:
				break

			counter += 1

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("found window_id=%s", window_id))

		return window_id

	def init_window_settings(self, window_id):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window_id))

		if window_id in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("already init"))

			return

		settings = get_settings(
			self._schema_source,
			'com.thingsthemselves.gedit.plugins.ex-mortis.restore-window',
			'/com/thingsthemselves/gedit/plugins/ex-mortis/restore-windows/' + window_id + '/'
		)

		self._window_settings[window_id] = settings

	def get_window_settings(self, window_id):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window_id))

		if window_id not in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("unknown window id"))

			return None

		return self._window_settings[window_id]

	def reset_window_settings(self, window_id):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("%s", window_id))

		if window_id not in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("unknown window id"))

			return

		settings = self._window_settings[window_id]

		for key in settings.keys():
			settings.reset(key)


def get_settings(schema_source, schema_id, settings_path):
	if log.query(log.INFO):
		Gedit.debug_plugin_message(log.format("schema_id=%s, settings_path=%s", schema_id, settings_path))

	if not schema_source:
		if log.query(log.CRITICAL):
			Gedit.debug_plugin_message(log.format("no schema source"))

		return None

	schema = schema_source.lookup(schema_id, False)

	if not schema:
		if log.query(log.CRITICAL):
			Gedit.debug_plugin_message(log.format("could not lookup '%s' in schema source", schema_id))

		return None

	return Gio.Settings.new_full(schema, None, settings_path)

