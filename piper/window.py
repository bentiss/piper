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


class _ButtonMapButton(Gtk.Button):
    # A Gtk.Button subclass to implement the button that configures a button
    # mapping according to the mockups.

    def __init__(self, ratbagd_button, *args, **kwargs):
        Gtk.Button.__init__(self, *args, **kwargs)
        self._button = ratbagd_button

        box = Gtk.Box(Gtk.Orientation.HORIZONTAL, border_width=0)
        button = Gtk.Label("Button {}".format(ratbagd_button.button_mapping))
        sep = Gtk.Separator.new(Gtk.Orientation.VERTICAL)
        cog = Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        box.pack_start(button, True, True, 4)
        box.pack_end(cog, False, True, 4)
        box.pack_end(sep, False, True, 4)
        self.add(box)

        self.connect("clicked", self._on_clicked)

    def _on_clicked(self, button):
        # Open the configuration dialog.
        builder = Gtk.Builder().new_from_resource("/org/freedesktop/Piper/buttonmapDialog.ui")
        builder.connect_signals(self)
        dialog = builder.get_object("buttonmap_dialog")
        dialog.set_transient_for(self.get_toplevel())
        status = dialog.run()
        if status == Gtk.ResponseType.ACCEPT:
            print("TODO: apply changes")
        dialog.destroy()

    def _on_set_clicked(self, dialog):
        # Emit the ::response signal with Gtk.ResponseType.ACCEPT so that
        # control is handed back to our main loop.
        dialog.response(Gtk.ResponseType.ACCEPT)

    def _on_cancel_clicked(self, dialog):
        # Emit the ::response signal with Gtk.ResponseType.CANCEL so that
        # control is handed back to our main loop.
        dialog.response(Gtk.ResponseType.CANCEL)


class _LedButton(Gtk.ButtonBox):
    # A Gtk.ButtonBox subclass to implement the buttons that configure an LED
    # according to the mockups.

    def __init__(self, ratbagd_led, *args, **kwargs):
        Gtk.ButtonBox.__init__(self, *args, **kwargs, orientation=Gtk.Orientation.HORIZONTAL)
        self.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        self._led = ratbagd_led

        for mode in ["Off", "On", "Cycle", "Breathing"]:
            button = Gtk.MenuButton(mode)
            self.pack_start(button, True, True, 0)


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
        stack.add_titled(self._setup_leds_page(device), "leds", _("LEDs"))
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
            mapbutton = _ButtonMapButton(button)
            mousemap.add(mapbutton, "#button{}".format(button.index))
            sizegroup.add_widget(mapbutton)
        return mousemap

    def _setup_leds_page(self, device):
        mousemap = MouseMap("#LEDs", device, spacing=20, border_width=20)
        sizegroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        profile = device.active_profile
        for led in profile.leds:
            ledbutton = _LedButton(led)
            mousemap.add(ledbutton, "#led{}".format(led.index))
            sizegroup.add_widget(ledbutton)
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
