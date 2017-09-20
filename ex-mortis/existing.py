# -*- coding: utf-8 -*-
#
# existing.py
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

from gi.repository import Gtk, Gedit

GETTEXT_PACKAGE = 'gedit-ex-mortis'
BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
	gettext.bindtextdomain(GETTEXT_PACKAGE, LOCALE_PATH)
	_ = lambda s: gettext.dgettext(GETTEXT_PACKAGE, s);
except:
	_ = lambda s: s


class Existing(object):
	def do_activate_existing(self):
		Gedit.debug_plugin_message("")

		self._existing = {}

	def do_deactivate_existing(self):
		Gedit.debug_plugin_message("")

		self._existing = None


	# setup

	def create_existing_info_bar(self):
		Gedit.debug_plugin_message("")

		screen_settings = Gtk.Settings.get_default()
		is_app_menu = not screen_settings.get_property('gtk-shell-shows-menubar')

		quit_response_id = Gtk.ResponseType.YES
		default_response_id = Gtk.ResponseType.CANCEL

		info_bar = Gtk.InfoBar.new()
		info_bar.add_button(_("_Quit"), quit_response_id)
		info_bar.add_button(_("_Ignore"), default_response_id)
		info_bar.set_message_type(Gtk.MessageType.WARNING)

		hbox_content = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 8)

		vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 6)

		hbox_content.pack_start(vbox, True, True, 0)

		primary_text = _("If you close this window, it cannot be reopened. Restart gedit to fully enable Ex-Mortis.")
		primary_markup = "<b>{}</b>".format(primary_text)

		primary_label = Gtk.Label.new(primary_markup)
		primary_label.set_use_markup(True)
		primary_label.set_line_wrap(True)
		primary_label.set_halign(Gtk.Align.START)
		primary_label.set_can_focus(True)
		primary_label.set_selectable(True)

		if is_app_menu:
			secondary_text = _("If you have enabled \"Restore windows between sessions\" in Ex-Mortis' preferences, this window can be restored if you quit gedit by selecting Quit in the Application menu or in this message.")
		else:
			secondary_text = _("If you have enabled \"Restore windows between sessions\" in Ex-Mortis' preferences, this window can be restored if you quit gedit by selecting Quit in the File menu or in this message.")
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

		return (info_bar, quit_response_id, default_response_id)


	# existing

	def is_existing(self, window):
		return hash(window) in self._existing

	def add_existing(self, window, info_bar):
		Gedit.debug_plugin_message("Window: %s, Info Bar: %s", hex(hash(window)), hex(hash(info_bar)))

		self._existing[hash(window)] = info_bar

	def remove_existing(self, window):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		if self.is_existing(window):
			del self._existing[hash(window)]

	def get_existing_info_bar(self, window):
		Gedit.debug_plugin_message("Window: %s", hex(hash(window)))

		info_bar = None

		if self.is_existing(window):
			info_bar = self._existing[hash(window)]

		return info_bar
