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

from gettext import gettext as _

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from .mousemap import MouseMap


class Window(Gtk.ApplicationWindow):
    """A Gtk.ApplicationWindow subclass to implement the main application
    window."""

    __gtype_name__ = "ApplicationWindow"

    def __init__(self, ratbag, *args, **kwargs):
        """Instantiates a new Window.

        @param ratbag The ratbag instance to connect to, as ratbagd.Ratbag
        """
        Gtk.ApplicationWindow.__init__(self, *args, **kwargs)
        self._ratbag = ratbag

        stack = Gtk.Stack()
        self.add(stack)
        stack.props.homogeneous = True
        stack.props.transition_duration = 500
        stack.props.transition_type = Gtk.StackTransitionType.SLIDE_LEFT_RIGHT

        device = self._fetch_ratbag_device()
        stack.add_titled(self._setup_buttons_page(device), "buttons", _("Buttons"))
        self.set_titlebar(self._setup_headerbar(stack))

    def _setup_headerbar(self, stack):
        headerbar = Gtk.HeaderBar()

        sizeGroup = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        self._quit = Gtk.Button.new_with_mnemonic(_("_Quit"))
        self._quit.connect("clicked", lambda button, data: data.destroy(), self)
        sizeGroup.add_widget(self._quit)
        headerbar.pack_start(self._quit)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(stack)
        headerbar.set_custom_title(switcher)

        return headerbar

    def _setup_buttons_page(self, device):
        mousemap = MouseMap("#Buttons", device, spacing=20, border_width=20)
        sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        profile = device.active_profile
        for button in profile.buttons:
            mapbutton = Gtk.Button("Button {}".format(button.index))
            mousemap.add(mapbutton, "#button{}".format(button.index))
            sizegroup.add_widget(mapbutton)
        return mousemap

    def _fetch_ratbag_device(self):
        """Get the first ratbag device available. If there are multiple
        devices, an error message is printed and we default to the first
        one. Otherwise, an error is shown and we return None.
        """
        if len(self._ratbag.devices) == 0:
            print("Could not find any devices. Do you have anything vaguely mouse-looking plugged in?")
            return None
        elif len(self._ratbag.devices) > 1:
            print("Ooops, can't deal with more than one device. My bad.")
            for d in self._ratbag.devices[1:]:
                print("Ignoring device {}".format(d.name))
        return self._ratbag.devices[0]
