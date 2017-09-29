# -*- coding: utf-8 -*-
#
# settings.py
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

import os.path
from gi.repository import GObject, Gio, Gedit
from .utils import debug_str
from . import log

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
SCHEMAS_PATH = os.path.join(BASE_PATH, 'schemas')


class ExMortisSettings(GObject.Object):

	__gtype_name__ = 'ExMortisSettings'

	restore_between_sessions = GObject.Property(type=bool, default=False)


	def __init__(self):
		GObject.Object.__init__(self)

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix())

		try:
			schema_source = Gio.SettingsSchemaSource.new_from_directory(
				SCHEMAS_PATH,
				Gio.SettingsSchemaSource.get_default(),
				False
			)

		except:
			if log.query(log.CRITICAL):
				Gedit.debug_plugin_message(log.prefix() + "could not load settings schema source from %s", SCHEMAS_PATH)

			schema_source = None

		settings = get_settings(
			schema_source,
			'com.thingsthemselves.gedit.plugins.ex-mortis',
			'/com/thingsthemselves/gedit/plugins/ex-mortis/'
		)

		if settings:
			settings.bind(
				'restore-between-sessions',
				self, 'restore_between_sessions',
				Gio.SettingsBindFlags.DEFAULT
			)

		self._schema_source = schema_source
		self._settings = settings
		self._window_settings = {}

		for window_id in self.window_ids:
			self.init_window_settings(window_id)

	def cleanup(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix())

		if self._settings:
			self._settings.unbind(self, 'restore_between_sessions')

		self._schema_source = None
		self._settings = None
		self._window_settings = None


	@property
	def can_save(self):
		return bool(self._settings)

	@property
	def window_ids(self):
		settings = self._settings
		return settings['restore-windows'] if settings else None

	@window_ids.setter
	def window_ids(self, window_ids):
		settings = self._settings
		if settings:
			settings['restore-windows'] = window_ids


	def add_window(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix())

		window_id = self.find_unused_window_id()

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "adding window_id=%s", window_id)

		self.init_window_settings(window_id)

		window_ids = self.window_ids
		window_ids.append(window_id)
		self.window_ids = window_ids

		return window_id

	def remove_window(self, window_id):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "window_id=%s", window_id)

		if window_id not in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.prefix() + "unknown window id")
			return

		self.reset_window_settings(window_id)

		window_ids = self.window_ids
		window_ids.remove(window_id)
		self.window_ids = window_ids

		del self._window_settings[window_id]

	def find_unused_window_id(self):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix())

		window_ids = self.window_ids
		window_id_map = {window_id : True for window_id in window_ids}
		counter = 0

		while True:
			window_id = 'window' + str(counter)

			if window_id not in window_id_map:
				break

			counter += 1

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "found window_id=%s", window_id)

		return window_id

	def init_window_settings(self, window_id):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "%s", window_id)

		if window_id in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.prefix() + "already init")
			return

		settings = get_settings(
			self._schema_source,
			'com.thingsthemselves.gedit.plugins.ex-mortis.restore-window',
			'/com/thingsthemselves/gedit/plugins/ex-mortis/restore-windows/' + window_id + '/'
		)

		self._window_settings[window_id] = settings

	def get_window_settings(self, window_id):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "%s", window_id)

		if window_id not in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.prefix() + "unknown window id")
			return None

		return self._window_settings[window_id]

	def reset_window_settings(self, window_id):
		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.prefix() + "%s", window_id)

		if window_id not in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.prefix() + "unknown window id")
			return

		settings = self._window_settings[window_id]

		for key in settings.keys():
			settings.reset(key)


def get_settings(schema_source, schema_id, settings_path):
	if log.query(log.INFO):
		Gedit.debug_plugin_message(log.prefix() + "schema_id=%s, settings_path=%s", schema_id, settings_path)

	if not schema_source:
		if log.query(log.CRITICAL):
			Gedit.debug_plugin_message(log.prefix() + "no schema source")
		return None

	schema = schema_source.lookup(schema_id, False)

	if not schema:
		if log.query(log.CRITICAL):
			Gedit.debug_plugin_message(log.prefix() + "could not lookup '%s' in schema source", schema_id)
		return None

	return Gio.Settings.new_full(schema, None, settings_path)

