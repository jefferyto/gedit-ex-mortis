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
from gi.repository import GLib, Gio, Gedit

BASE_PATH = os.path.dirname(os.path.realpath(__file__))


class Settings(object):
	SETTINGS_SCHEMA_ID = 'com.thingsthemselves.gedit.plugins.ex-mortis'

	SETTINGS_RESTORE_BETWEEN_SESSIONS = 'restore-between-sessions'

	SETTINGS_RESTORE_URIS = 'restore-uris'
	SETTINGS_RESTORE_URIS_GVARIANT_TYPE = 'aaas'


	def do_activate_settings(self):
		Gedit.debug_plugin_message("")

		schemas_path = os.path.join(BASE_PATH, 'schemas')

		try:
			schema_source_default = Gio.SettingsSchemaSource.get_default()
			schema_source = Gio.SettingsSchemaSource.new_from_directory(
				schemas_path, schema_source_default, False
			)
			schema = Gio.SettingsSchemaSource.lookup(
				schema_source, self.SETTINGS_SCHEMA_ID, False
			)
			settings = Gio.Settings.new_full(schema, None, None) if schema else None

		except:
			Gedit.debug_plugin_message("could not load settings schema from %s", schemas_path)
			settings = None

		self._settings = settings

	def do_deactivate_settings(self):
		Gedit.debug_plugin_message("")

		self._settings = None


	# settings

	def get_settings(self):
		Gedit.debug_plugin_message("")

		return self._settings


	# settings-specific getters/setters

	def get_settings_restore_between_sessions(self):
		settings = self._settings
		return settings and settings.get_boolean(self.SETTINGS_RESTORE_BETWEEN_SESSIONS)

	def set_settings_restore_between_sessions(self, is_enabled):
		settings = self._settings

		if settings:
			settings.set_boolean(self.SETTINGS_RESTORE_BETWEEN_SESSIONS, is_enabled)

	def get_settings_restore_uris(self):
		settings = self._settings
		return settings.get_value(self.SETTINGS_RESTORE_URIS) if settings else None

	def set_settings_restore_uris(self, window_uris_map):
		settings = self._settings

		if settings:
			value = []

			if window_uris_map and self.get_settings_restore_between_sessions():
				value = [
					window_uris
					for window_uris in window_uris_map.values()
					if window_uris
				]

			gvariant_value = GLib.Variant(self.SETTINGS_RESTORE_URIS_GVARIANT_TYPE, value)
			settings.set_value(self.SETTINGS_RESTORE_URIS, gvariant_value)


	# settings-specific signal names

	def get_settings_signal_changed_restore_between_sessions(self):
		return 'changed::' + self.SETTINGS_RESTORE_BETWEEN_SESSIONS
