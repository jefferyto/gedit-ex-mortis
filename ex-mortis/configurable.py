# -*- coding: utf-8 -*-
#
# configurable.py
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
gi.require_version('Gedit', '3.0')
gi.require_version('Gio', '2.0')
gi.require_version('Gtk', '3.0')
gi.require_version('PeasGtk', '1.0')

from gi.repository import GObject, Gedit, Gio, Gtk, PeasGtk
from .plugin import _
from .settings import ExMortisSettings
from .utils import create_bindings
from . import log


class ExMortisConfigurable(GObject.Object, PeasGtk.Configurable):

	__gtype_name__ = 'ExMortisConfigurable'


	def do_create_configure_widget(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		app = Gedit.App.get_default()
		is_primary = not (app.get_flags() & Gio.ApplicationFlags.NON_UNIQUE)
		settings = ExMortisSettings()

		if settings.can_save:
			widget = Gtk.CheckButton.new_with_label(
				_("Restore windows between sessions")
			)

			if not is_primary:
				widget.set_sensitive(False)

			create_bindings(
				self, settings, widget,
				{'restore_between_sessions': 'active'},
				GObject.BindingFlags.BIDIRECTIONAL
			)

			widget.set_active(settings.restore_between_sessions)
			widget._settings = settings

		else:
			widget = Gtk.Label.new(_("Could not load settings schema"))

		box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
		box.set_border_width(5)
		box.add(widget)

		return box

