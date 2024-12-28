# -*- coding: utf-8 -*-
#
# existingmixin.py
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
gi.require_version('Gedit', '3.0')
gi.require_version('Gtk', '3.0')

from gi.repository import Gedit, Gtk
from .plugin import _
from . import log


class ExMortisAppActivatableExistingMixin(object):

	EXISTING_INFO_BAR_RESPONSE_QUIT = Gtk.ResponseType.YES

	EXISTING_INFO_BAR_RESPONSE_IGNORE = Gtk.ResponseType.CANCEL


	def do_activate_existing(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		self._existing = {}

	def do_deactivate_existing(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		self._existing = None


	# info bar

	def create_existing_info_bar(self):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format(""))

		screen_settings = Gtk.Settings.get_default()
		is_app_menu = not screen_settings.get_property('gtk-shell-shows-menubar')

		info_bar = Gtk.InfoBar.new()
		info_bar.add_button(_("_Quit"), self.EXISTING_INFO_BAR_RESPONSE_QUIT)
		info_bar.add_button(_("_Ignore"), self.EXISTING_INFO_BAR_RESPONSE_IGNORE)
		info_bar.set_message_type(Gtk.MessageType.WARNING)

		hbox_content = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 8)

		vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 6)

		hbox_content.pack_start(vbox, True, True, 0)

		primary_text = _("This window cannot be reopened if closed. Restart gedit to fully enable Ex-Mortis.")
		primary_markup = "<b>{}</b>".format(primary_text)

		primary_label = Gtk.Label.new(primary_markup)
		primary_label.set_use_markup(True)
		primary_label.set_line_wrap(True)
		primary_label.set_halign(Gtk.Align.START)
		primary_label.set_can_focus(True)
		primary_label.set_selectable(True)

		secondary_text_pref = _("Restore windows between sessions")
		secondary_text_menu = _("Application menu") if is_app_menu else _("File menu")
		secondary_text = _("To restore this window, enable \"{pref_name}\" in Ex-Mortis' preferences, and quit gedit by selecting Quit in the {menu_name} or in this message.").format(pref_name=secondary_text_pref, menu_name=secondary_text_menu)
		secondary_markup = "<small>{}</small>".format(secondary_text)

		secondary_label = Gtk.Label.new(secondary_markup)
		secondary_label.set_use_markup(True)
		secondary_label.set_line_wrap(True)
		secondary_label.set_halign(Gtk.Align.START)
		secondary_label.set_can_focus(True)
		secondary_label.set_selectable(True)

		vbox.pack_start(primary_label, True, True, 0)
		vbox.pack_start(secondary_label, True, True, 0)

		hbox_content.show_all()

		content_area = info_bar.get_content_area()
		content_area.add(hbox_content)

		return info_bar

	def pack_existing_info_bar(self, window, info_bar):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		hpaned = window.get_template_child(Gedit.Window, 'hpaned')
		main_box = hpaned.get_parent()
		num_children = len(main_box.get_children())

		main_box.pack_start(info_bar, False, False, 0)
		# on DEs where there is a separate title bar, e.g. Unity
		# the header bar is a child element here
		# other DEs, e.g. GNOME Shell, the header bar is... somewhere else?
		main_box.reorder_child(info_bar, num_children - 1)


	# existing

	def is_existing(self, window):
		return window in self._existing

	def add_existing(self, window):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		if self.is_existing(window):
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Already added %s", window))

			# disconnect handlers?

			self.remove_existing(window)

		info_bar = self.create_existing_info_bar()

		self._existing[window] = info_bar

		return (info_bar, self.EXISTING_INFO_BAR_RESPONSE_QUIT)

	def show_existing_info_bar(self, window):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not self.is_existing(window):
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Not existing %s", window))

			return

		info_bar = self._existing[window]

		self.pack_existing_info_bar(window, info_bar)

		# must be done after the info bar is added to the window
		info_bar.set_default_response(self.EXISTING_INFO_BAR_RESPONSE_IGNORE)

		info_bar.show()

	def get_existing_info_bar(self, window):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not self.is_existing(window):
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Not existing %s", window))

			return None

		return self._existing[window]

	def remove_existing(self, window):
		if log.query(log.DEBUG):
			Gedit.debug_plugin_message(log.format("%s", window))

		if not self.is_existing(window):
			if log.query(log.WARNING):
				Gedit.debug_plugin_message(log.format("Not existing %s", window))

			return

		info_bar = self._existing[window]
		info_bar.destroy()

		del self._existing[window]

