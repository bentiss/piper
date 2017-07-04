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
from gi.repository import GObject, Gtk

from .mousemap import MouseMap
from .gi_composites import GtkTemplate


@GtkTemplate(ui="/org/freedesktop/Piper/resolutionRow.ui")
class _ResolutionRow(Gtk.ListBoxRow):
    # A Gtk.ListBoxRow subclass to implement the resolution listbox according
    # to the mockups.

    __gtype_name__ = "ResolutionRow"

    index_label = GtkTemplate.Child()
    rate_label = GtkTemplate.Child()
    revealer = GtkTemplate.Child()
    frame_y = GtkTemplate.Child()
    adjustment_x = GtkTemplate.Child()
    adjustment_y = GtkTemplate.Child()

    def __init__(self, ratbagd_resolution, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.init_template()
        self._resolution = ratbagd_resolution

        self.index_label.set_text("Resolution {}".format(ratbagd_resolution.index))
        # TODO: move the report rate into the configuration? it seems to be per
        # resolution...
        self.rate_label.set_text("{} DPI".format(ratbagd_resolution.resolution_x))

        flags = GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE
        cap = ratbagd_resolution.CAP_SEPARATE_XY_RESOLUTION

        self.frame_y.set_visible(cap in ratbagd_resolution.capabilities)
        self.adjustment_y.set_lower(ratbagd_resolution.min_res)
        self.adjustment_y.set_upper(ratbagd_resolution.max_res)
        ratbagd_resolution.bind_property("resolution-y", self.adjustment_y,
                                         "value", flags)
        self.adjustment_x.set_lower(ratbagd_resolution.min_res)
        self.adjustment_x.set_upper(ratbagd_resolution.max_res)
        ratbagd_resolution.bind_property("resolution-x", self.adjustment_x,
                                         "value", flags)

    @GtkTemplate.Callback
    def _on_delete_button_clicked(self, button):
        print("TODO: RatbagdProfile needs a way to delete resolutions")

    def toggle_revealer(self):
        """Toggles the revealer to show or hide the configuration widgets."""
        reveal = not self.revealer.get_reveal_child()
        self.revealer.set_reveal_child(reveal)


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


@GtkTemplate(ui="/org/freedesktop/Piper/window.ui")
class Window(Gtk.ApplicationWindow):
    """A Gtk.ApplicationWindow subclass to implement the main application
    window."""

    __gtype_name__ = "ApplicationWindow"

    stack = GtkTemplate.Child()
    listbox = GtkTemplate.Child()
    add_resolution_row = GtkTemplate.Child()

    def __init__(self, ratbag, *args, **kwargs):
        """Instantiates a new Window.

        @param ratbag The ratbag instance to connect to, as ratbagd.Ratbag
        """
        Gtk.ApplicationWindow.__init__(self, *args, **kwargs)
        self.init_template()

        self._ratbag = ratbag
        self._device = self._fetch_ratbag_device()
        self._previous_resolution_row = None

        self._setup_resolutions_page(self._device)
        self.stack.add_titled(self._setup_buttons_page(self._device), "buttons", _("Buttons"))
        self.stack.add_titled(self._setup_leds_page(self._device), "leds", _("LEDs"))

    def _setup_resolutions_page(self, device):
        # TODO: mousemap needs to show which button switches resolution
        mousemap = MouseMap("#Device", device, spacing=20, border_width=20)

        page = self.stack.get_child_by_name("resolutions")
        page.pack_start(mousemap, True, True, 0)
        # Place the MouseMap on the left
        page.reorder_child(mousemap, 0)

        profile = device.active_profile
        for resolution in profile.resolutions:
            row = _ResolutionRow(resolution)
            self.listbox.prepend(row)

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

    @GtkTemplate.Callback
    def _on_row_activated(self, listbox, row):
        if row == self.add_resolution_row:
            print("TODO: RatbagdProfile needs a way to add resolutions")
        elif row is not None:
            row.toggle_revealer()

    @GtkTemplate.Callback
    def _on_save_button_clicked(self, button):
        self._device.commit()
