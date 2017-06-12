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

import cairo
import gi
import os
import sys
from lxml import etree

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Rsvg", "2.0")
from gi.repository import Gdk, GLib, Gtk, GObject, Rsvg

"""This module contains the MouseMap widget (and its helper class
_MouseMapChild), which is central to the button and LED configuration stack
pages. The MouseMap widget draws the device SVG in the center and lays out a
bunch of child widgets relative to the leaders in the device SVG."""


class _MouseMapChild:
    # A helper class to manage children and their properties.

    def __init__(self, widget, is_left, svg_id):
        self._widget = widget
        self._is_left = is_left
        self._svg_id = svg_id
        self._svg_leader = svg_id + "-leader"

    @property
    def widget(self):
        # The widget belonging to this child.
        return self._widget

    @property
    def svg_id(self):
        # The identifier of the SVG element with which this child's widget is
        # paired.
        return self._svg_id

    @property
    def svg_leader(self):
        # The identifier of the leader SVG element with which this child's
        # widget is paired.
        return self._svg_leader

    @property
    def is_left(self):
        # True iff this child's widget is allocated to the left of the SVG.
        return self._is_left


class MouseMap(Gtk.Container):
    """A Gtk.Container subclass to draw a device SVG with child widgets that
    map to the SVG. The SVG should have objects with identifiers, whose value
    should also be given to the `add` method. See `do_size_allocate` and
    https://github.com/libratbag/libratbag/blob/master/data/README.md for more
    information.
    """

    __gtype_name__ = "MouseMap"

    __gproperties__ = {
        "spacing": (int,
                    "spacing",
                    "The amount of space between children and the SVG leaders",
                    0, GLib.MAXINT, 0,
                    GObject.PARAM_READABLE),
    }

    def __init__(self, layer, ratbagd_device, spacing=10, *args, **kwargs):
        """Instantiates a new MouseMap.

        @param layer The SVG layer whose leaders to draw, according to librsvg
                     so e.g. `#layer1`.
        @param ratbagd_device The device that should be mapped, as
                              ratbagd.RatbagdDevice
        @param spacing The spacing to place between the SVG's leaders and the
                       widgets, as int

        @raises ValueError when an argument is invalid, or when the given device
                           has no image registered.
        @raises GLib.Error when the SVG cannot be loaded.
        """
        if layer is None:
            raise ValueError("Layer cannot be None")
        if ratbagd_device is None:
            raise ValueError("Device cannot be None")
        if not os.path.isfile(ratbagd_device.svg_path):
            raise ValueError("Device has no image or its path is invalid")

        Gtk.Container.__init__(self, *args, **kwargs)
        self.set_has_window(False)

        self.spacing = spacing
        self._layer = layer
        self._device = ratbagd_device
        self._children = []
        self._highlight_element = None

        self._handle = Rsvg.Handle.new_from_file(ratbagd_device.svg_path)
        self._svg_data = etree.parse(ratbagd_device.svg_path)

    def add(self, widget, svg_id):
        """Adds the given widget to the map, bound to the given SVG element
        identifier. If the element identifier or its leader is not found in the
        SVG, the widget is not added.

        @param widget The widget to add, as Gtk.Widget
        @param svg_id The identifier of the SVG element with which this widget
                      is to be paired, as str
        """
        svg_leader = svg_id + "-leader"
        if widget is None or svg_id is None or not \
            self._handle.has_sub(svg_id) or not \
                self._handle.has_sub(svg_leader):
            return

        is_left = self._xpath_has_style(svg_leader[1:], "text-align:end")
        child = _MouseMapChild(widget, is_left, svg_id)
        self._children.append(child)
        widget.connect("enter-notify-event", self._on_enter, child)
        widget.connect("leave-notify-event", self._on_leave)
        widget.set_parent(self)

    def do_remove(self, widget):
        """Removes the given widget from the map.

        @param widget The widget to remove, as Gtk.Widget
        """
        if widget is not None:
            for child in self._children:
                if child.widget == widget:
                    self._children.remove(child)
                    child.widget.unparent()
                    break

    def do_child_type(self):
        """Indicates that this container accepts any GTK+ widget."""
        return Gtk.Widget.get_type()

    def do_forall(self, include_internals, callback, *parameters):
        """Invokes the given callback on each child, with the given parameters.

        @param include_internals Whether to run on internal children as well,
                                 as boolean. Ignored, as there are no internal
                                 children.
        @param callback The callback to call on each child, as Gtk.Callback
        @param parameters The parameters to pass to the callback, as object or
                          None.
        """
        if callback is not None:
            for child in self._children:
                callback(child.widget, *parameters)

    def do_get_request_mode(self):
        """Gets whether the container prefers a height-for-width or a
        width-for-height layout. We don't want to trade width for height or
        height for width so we return CONSTANT_SIZE."""
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_get_preferred_height(self):
        """Calculates the container's initial minimum and natural height. While
        this call is specific to width-for-height requests (that we requested
        not to get) we cannot be certain that our wishes are granted and hence
        we must implement this method as well. We just return the SVG's height
        plus the border widths.
        """
        # TODO: account for children sticking out under or above the SVG, if
        # they exist. At the moment we cannot reliably do so because the
        # y-coordinates of the leaders can have any arbitrary value. For now,
        # we assume that the SVG is high enough to fit all children and do not
        # worry about setups beyond the default GNOME Adwaita.
        height = self._handle.props.height + 2 * self.props.border_width
        return (height, height)

    def do_get_preferred_width(self):
        """Calculates the container's initial minimum and natural width. While
        this call is specific to height-for-width requests (that we requested
        not to get) we cannot be certain that our wishes are granted and hence
        we must implement this method as well. We return the sum of the SVG's
        width, the natural child widths (left and right), spacing and border
        width.
        """
        width = 2 * self.props.border_width
        width_svg = self._handle.props.width
        width_left = [child.widget.get_preferred_width()[1] for child in
                      self._children if child.is_left]
        width_right = [child.widget.get_preferred_width()[1] for child in
                       self._children if not child.is_left]
        width_left = max(width_left, default=0)
        width_right = max(width_right, default=0)
        width += width_left + width_svg + width_right + self.spacing
        if width_left > 0:
            width += self.spacing
        return (width, width)

    def do_get_preferred_height_for_width(self, width):
        """Returns this container's minimum and natural height if it would be
        given the specified width. While this call is specific to
        height-for-width requests (that we requested not to get) we cannot be
        certain that our wishes are granted and hence we must implement this
        method as well. Since we really want to be the same size always, we
        simply return do_get_preferred_height.

        @param width The given width, as int. Ignored.
        """
        return self.do_get_preferred_height()

    def do_get_preferred_width_for_height(self, height):
        """Returns this container's minimum and natural width if it would be
        given the specified height. While this call is specific to
        width-for-height requests (that we requested not to get) we cannot be
        certain that our wishes are granted and hence we must implement this
        method as well. Since we really want to be the same size always, we
        simply return do_get_preferred_width.

        @param height The given height, as int. Ignored.
        """
        return self.do_get_preferred_width()

    def do_size_allocate(self, allocation):
        """Assigns a size and position to the child widgets. Children may
        adjust the given allocation in their adjust_size_allocation virtual
        method implementation.

        @param allocation The position and size allocated to this container, as
                          Gdk.Rectangle
        """
        self.set_allocation(allocation)
        x, y = self._translate_to_origin()
        child_allocation = Gdk.Rectangle()

        for child in self._children:
            if not child.widget.get_visible():
                continue
            svg_geom = self._get_svg_sub_geometry(child.svg_leader)[1]
            nat_size = child.widget.get_preferred_size()[1]
            if child.is_left:
                child_allocation.x = x + svg_geom.x - self.spacing - nat_size.width
            else:
                child_allocation.x = x + svg_geom.x + self.spacing
            child_allocation.y = y + svg_geom.y + 0.5 * svg_geom.height - 0.5 * nat_size.height
            child_allocation.width = nat_size.width
            child_allocation.height = nat_size.height
            if not child.widget.get_has_window():
                child_allocation.x += allocation.x
                child_allocation.y += allocation.y
            child.widget.size_allocate(child_allocation)

    def do_draw(self, cr):
        """Draws the container to the given Cairo context. The top left corner
        of the widget will be drawn to the currently set origin point of the
        context. The container needs to propagate the draw signal to its
        children.

        @param cr The Cairo context to draw into, as cairo.Context
        """
        cr.save()
        x, y = self._translate_to_origin()
        cr.translate(x, y)
        self._draw_device(cr)
        cr.restore()
        for child in self._children:
            self.propagate_draw(child.widget, cr)

    def do_get_property(self, prop):
        """Gets a property value.

        @param prop The property to get, as GObject.ParamSpec
        """
        if prop.name == "spacing":
            return self.spacing
        else:
            raise AttributeError("Unknown property %s" % prop.name)

    def _on_enter(self, widget, event, child):
        # Highlights the element in the SVG to which the given widget belongs.
        self._highlight_element = child.svg_id
        self._redraw_svg_element(child.svg_id)

    def _on_leave(self, widget, event):
        # Restores the device SVG to its original state.
        old_highlight = self._highlight_element
        self._highlight_element = None
        self._redraw_svg_element(old_highlight)

    def _xpath_has_style(self, svg_id, style):
        # Checks if the SVG element with the given identifier has the given
        # style attribute set.
        namespaces = {
            'sodipodi': 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
            'cc': 'http://web.resource.org/cc/',
            'svg': 'http://www.w3.org/2000/svg',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'xlink': 'http://www.w3.org/1999/xlink',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'inkscape': 'http://www.inkscape.org/namespaces/inkscape'
        }
        query = "//svg:rect[@id=\"{}\"][contains(@style, \"{}\")]".format(svg_id, style)
        element = self._svg_data.xpath(query, namespaces=namespaces)
        return element is not None and len(element) == 1 and element[0] is not None

    def _get_svg_sub_geometry(self, svg_id):
        # Helper method to get an SVG element's x- and y-coordinates, width and
        # height.
        ret = Gdk.Rectangle()
        ok, svg_pos = self._handle.get_position_sub(svg_id)
        if not ok:
            print("Warning: cannot retrieve element's position:", svg_id,
                  file=sys.stderr)
            return ok, ret
        ret.x = svg_pos.x
        ret.y = svg_pos.y

        ok, svg_dim = self._handle.get_dimensions_sub(svg_id)
        if not ok:
            print("Warning: cannot retrieve element's dimensions:", svg_id,
                  file=sys.stderr)
            return ok, ret
        ret.width = svg_dim.width
        ret.height = svg_dim.height
        return ok, ret

    def _redraw_svg_element(self, svg_id):
        # Helper method to redraw an element of the SVG image. Attempts to
        # redraw only the element (plus an offset), but will fall back to
        # redrawing the complete SVG.
        x, y = self._translate_to_origin()
        ok, svg_geom = self._get_svg_sub_geometry(svg_id)
        if not ok:
            svg_width = self._handle.props.width
            svg_height = self._handle.props.height
            self.queue_draw_area(x, y, svg_width, svg_height)
        else:
            self.queue_draw_area(x + svg_geom.x - 10, y + svg_geom.y - 10,
                                 svg_geom.width + 20, svg_geom.height + 20)

    def _translate_to_origin(self):
        # Translates the coordinate system such that the SVG and its buttons
        # will be drawn in the center of the allocated space. The returned x-
        # and y-coordinates will be the top left corner of the centered SVG.
        allocation = self.get_allocation()
        width = self.get_preferred_width()[1]
        height = self.get_preferred_height()[1]

        width_left = [child.widget.get_preferred_width()[1] for child in
                      self._children if child.is_left]
        width_left = max(width_left, default=0)
        if width_left > 0:
            width_left += self.spacing

        x = (allocation.width - width) / 2 + self.props.border_width + width_left
        y = (allocation.height - height) / 2 + self.props.border_width
        return round(x), round(y)

    def _draw_device(self, cr):
        # Draws the SVG into the Cairo context. If there is an element to be
        # highlighted, it will do as such in a separate surface which will be
        # used as a mask over the device surface.
        color = self.get_style_context().get_color(Gtk.StateFlags.LINK)
        cr.set_source_rgba(color.red, color.green, color.blue, 0.5)

        self._handle.render_cairo_sub(cr, id="#Device")
        if self._highlight_element is not None:
            svg_surface = cr.get_target()
            highlight_surface = svg_surface.create_similar(cairo.CONTENT_COLOR_ALPHA,
                                                           self._handle.props.width,
                                                           self._handle.props.height)
            highlight_context = cairo.Context(highlight_surface)
            self._handle.render_cairo_sub(highlight_context,
                                          self._highlight_element)
            cr.mask_surface(highlight_surface, 0, 0)
        self._handle.render_cairo_sub(cr, id=self._layer)
