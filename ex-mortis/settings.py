# -*- coding: utf-8 -*-
#
# settings.py
# This file is part of Ex-Mortis, a plugin for gedit
#
# Copyright (C) 2017-2019, 2023-2024 Jeffery To <jeffery.to@gmail.com>
# https://github.com/jefferyto/gedit-ex-mortis
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

import gi
gi.require_version('GObject', '2.0')
gi.require_version('Gedit', '3.0')
gi.require_version('Gio', '2.0')

import os.path
from gi.repository import GObject, Gedit, Gio
from .plugin import data_dir as plugin_data_dir
from . import log


class ExMortisSettings(GObject.Object):

	__gtype_name__ = 'ExMortisSettings'

	restore_between_sessions = GObject.Property(type=bool, default=False)

	restore_windows = GObject.Property(type=GObject.GType.from_name('GStrv'), default=[])

	backup_restore_windows = GObject.Property(type=GObject.GType.from_name('GStrv'), default=[])


	def __init__(self, is_enabled=True):
		GObject.Object.__init__(self)

		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("is_enabled=%s", is_enabled))

		schemas_directory = os.path.join(plugin_data_dir, 'schemas')
		default_schema_source = Gio.SettingsSchemaSource.get_default()

		try:
			schema_source = Gio.SettingsSchemaSource.new_from_directory(
				schemas_directory,
				default_schema_source,
				False
			)

		except:
			if log.query(log.INFO):
				Gedit.debug_plugin_message(log.format("Could not load schema source from %s", schemas_directory))

			schema_source = None

		if not schema_source:
			schema_source = default_schema_source

		if is_enabled:
			settings = get_settings(
				schema_source,
				'com.thingsthemselves.gedit.plugins.ex-mortis'
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
		if log.query(log.DEBUG):
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

	@property
	def have_backup(self):
		return bool(self.backup_restore_windows)


	def add_window(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		window_id = self.find_unused_window_id()

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("Adding window id %s", window_id))

		self.init_window_settings(window_id)

		restore_windows = self.restore_windows
		restore_windows.append(window_id)
		self.restore_windows = restore_windows

		return window_id

	def remove_windows(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		for window_id in list(self.restore_windows):
			self.remove_window(window_id)

	def remove_window(self, window_id):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("window_id=%s", window_id))

		if window_id not in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Unknown window id %s", window_id))

			return

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("Removing window id %s", window_id))

		self.reset_window_settings(window_id)

		restore_windows = self.restore_windows
		restore_windows.remove(window_id)
		self.restore_windows = restore_windows

		del self._window_settings[window_id]

	def find_unused_window_id(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		window_id_set = set(self.restore_windows)
		counter = 0

		while True:
			window_id = 'window' + str(counter)

			if window_id not in window_id_set:
				break

			counter += 1

		if log.query(log.INFO):
			Gedit.debug_plugin_message(log.format("Found unused window id %s", window_id))

		return window_id

	def init_window_settings(self, window_id):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("window_id=%s", window_id))

		if window_id in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Already init for window id %s", window_id))

			return

		settings = get_window_settings(self._schema_source, window_id)
		self._window_settings[window_id] = settings

	def get_window_settings(self, window_id):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("window_id=%s", window_id))

		if window_id not in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Unknown window id %s", window_id))

			return None

		return self._window_settings[window_id]

	def reset_window_settings(self, window_id):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("window_id=%s", window_id))

		if window_id not in self._window_settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Unknown window id %s", window_id))

			return

		settings = self._window_settings[window_id]

		if not settings:
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("No settings for window id %s", window_id))

			return

		reset_settings(settings)

	def save_backup(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		if not self.can_save:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("Not modifying settings"))

			return

		self.clear_backup()

		schema_source = self._schema_source
		restore_windows = self.restore_windows

		for window_id in restore_windows:
			window_settings = self.get_window_settings(window_id)
			backup_window_settings = get_window_settings(schema_source, window_id, backup=True)

			if not window_settings:
				if log.query(log.WARNING):
					Gedit.debug_plugin_message(log.format("Could not get settings for window id %s", window_id))

				continue

			if not backup_window_settings:
				if log.query(log.WARNING):
					Gedit.debug_plugin_message(log.format("Could not get backup settings for window id %s", window_id))

				continue

			copy_settings(window_settings, backup_window_settings)

		self.backup_restore_windows = restore_windows

		Gio.Settings.sync()

	def restore_backup(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		if not self.can_save:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("Not modifying settings"))

			return

		self.remove_windows()

		schema_source = self._schema_source

		for backup_window_id in self.backup_restore_windows:
			backup_window_settings = get_window_settings(schema_source, backup_window_id, backup=True)

			if not backup_window_settings:
				if log.query(log.WARNING):
					Gedit.debug_plugin_message(log.format("Could not get backup settings for window id %s", backup_window_id))

				continue

			window_id = self.add_window()
			window_settings = self.get_window_settings(window_id)

			if not window_settings:
				if log.query(log.WARNING):
					Gedit.debug_plugin_message(log.format("Could not get settings for window id %s", window_id))

				continue

			copy_settings(backup_window_settings, window_settings)

	def clear_backup(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		if not self.can_save:
			if log.query(log.DEBUG):
				Gedit.debug_plugin_message(log.format("Not modifying settings"))

			return

		schema_source = self._schema_source

		for backup_window_id in self.backup_restore_windows:
			backup_window_settings = get_window_settings(schema_source, backup_window_id, backup=True)

			if not backup_window_settings:
				if log.query(log.WARNING):
					Gedit.debug_plugin_message(log.format("Could not get backup settings for window id %s", backup_window_id))

				continue

			reset_settings(backup_window_settings)

		self._settings.reset('backup-restore-windows')

		Gio.Settings.sync()

def get_window_settings(schema_source, window_id, backup=False):
	if log.query(log.DEBUG):
		Gedit.debug_plugin_message(log.format("window_id=%s, backup=%s", window_id, backup))

	schema_id = 'com.thingsthemselves.gedit.plugins.ex-mortis.restore-window'

	settings_base_path = '/com/thingsthemselves/gedit/plugins/ex-mortis/'
	settings_dir = 'restore-windows/' if not backup else 'backup-restore-windows/'
	settings_path = settings_base_path + settings_dir + window_id + '/'

	return get_settings(schema_source, schema_id, settings_path)

def get_settings(schema_source, schema_id, settings_path=None):
	if log.query(log.DEBUG):
		Gedit.debug_plugin_message(log.format("schema_id=%s, settings_path=%s", schema_id, settings_path))

	schema = schema_source.lookup(schema_id, True)
	return Gio.Settings.new_full(schema, None, settings_path) if schema else None

def copy_settings(source, destination):
	if log.query(log.DEBUG):
		Gedit.debug_plugin_message(log.format(""))

	for key in source.keys():
		destination[key] = source[key]

def reset_settings(settings):
	if log.query(log.DEBUG):
		Gedit.debug_plugin_message(log.format(""))

	for key in settings.keys():
		settings.reset(key)

