# Copyright (C) 2017 Jente Hidskes <hjdskes@gmail.com>
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
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import gi
gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk

from .ratbagd import Ratbagd, RatbagdDBusUnavailable
from .window import Window


class Application(Gtk.Application):
    """A Gtk.Application subclass to handle the application's initialization and
    integration with the GNOME stack. It implements the do_startup and
    do_activate methods and is responsible for the application's menus, icons,
    title and lifetime."""

    def __init__(self):
        """Instantiates a new Application."""
        Gtk.Application.__init__(self, application_id="org.freedesktop.Piper",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name("Piper")

    def do_startup(self):
        """This function is called when the application is first started. All
        initialization should be done here, to prevent doing duplicate work in
        case another window is opened."""
        Gtk.Application.do_startup(self)
        self._build_app_menu()
        try:
            self._ratbag = Ratbagd()
        except RatbagdDBusUnavailable:
            self._ratbag = None

    def do_activate(self):
        """This function is called when the user requests a new window to be
        opened."""
        try:
            window = Window(self._ratbag, application=self)
            window.show_all()
            window.present()
        except ValueError as e:
            self._present_error_dialog(e)
        except GLib.Error as e:
            self._present_error_dialog(e.message)

    def _present_error_dialog(self, message):
        # Present an error dialog informing the user of any errors.
        # TODO: this should be something in the main window instead, according
        # to the mockups.
        print("Cannot create window: {}".format(message))

    def _build_app_menu(self):
        # Set up the app menu
        actions = [("about", self._about), ("quit", self._quit)]
        for (name, callback) in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def _about(self, action, param):
        # Set up the about dialog.
        builder = Gtk.Builder().new_from_resource("/org/freedesktop/Piper/aboutDialog.ui")
        about = builder.get_object("about_dialog")
        about.set_transient_for(self.get_active_window())
        about.show()

    def _quit(self, action, param):
        # Quit the application.
        windows = self.get_windows()
        for window in windows:
            window.destroy()
