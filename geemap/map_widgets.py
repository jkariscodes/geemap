"""Various ipywidgets that can be added to a map."""

import functools

import IPython
from IPython.core.display import HTML, display

import ee
import ipytree
import ipywidgets

from . import common

from traceback import format_tb


def _set_css_in_cell_output():
    display(
        HTML(
            """
            <style>
                .geemap-dark {
                    --jp-widgets-color: white;
                    --jp-widgets-label-color: white;
                    --jp-ui-font-color1: white;
                    --jp-layout-color2: #454545;
                    background-color: #383838;
                }
                    
                .geemap-dark .jupyter-button {
                    --jp-layout-color3: #383838;
                }
                
                .geemap-colab {
                    background-color: var(--colab-primary-surface-color, white);
                }
                    
                .geemap-colab .jupyter-button {
                    --jp-layout-color3: var(--colab-primary-surface-color, white);
                }
            </style>
            """
        )
    )


try:
    IPython.get_ipython().events.register("pre_run_cell", _set_css_in_cell_output)
except AttributeError:
    pass


class Theme:
    """Applies dynamic theme in Colab, otherwise light."""

    current_theme = "colab" if common.in_colab_shell() else "light"

    @staticmethod
    def apply(cls):
        original_init = cls.__init__

        @functools.wraps(cls.__init__)
        def wrapper(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.add_class("geemap-{}".format(Theme.current_theme))

        cls.__init__ = wrapper
        return cls


@Theme.apply
class Colorbar(ipywidgets.Output):
    """A matplotlib colorbar widget that can be added to the map."""

    def __init__(
        self,
        vis_params=None,
        cmap="gray",
        discrete=False,
        label=None,
        orientation="horizontal",
        transparent_bg=False,
        font_size=9,
        axis_off=False,
        max_width=None,
        **kwargs,
    ):
        """Add a matplotlib colorbar to the map.

        Args:
            vis_params (dict): Visualization parameters as a dictionary. See
                https://developers.google.com/earth-engine/guides/image_visualization # noqa
                for options.
            cmap (str, optional): Matplotlib colormap. Defaults to "gray". See
                https://matplotlib.org/3.3.4/tutorials/colors/colormaps.html#sphx-glr-tutorials-colors-colormaps-py # noqa
                for options.
            discrete (bool, optional): Whether to create a discrete colorbar.
                Defaults to False.
            label (str, optional): Label for the colorbar. Defaults to None.
            orientation (str, optional): Orientation of the colorbar, such as
                "vertical" and "horizontal". Defaults to "horizontal".
            transparent_bg (bool, optional): Whether to use transparent
                background. Defaults to False.
            font_size (int, optional): Font size for the colorbar. Defaults
                to 9.
            axis_off (bool, optional): Whether to turn off the axis. Defaults
                to False.
            max_width (str, optional): Maximum width of the colorbar in pixels.
                Defaults to None.

        Raises:
            TypeError: If the vis_params is not a dictionary.
            ValueError: If the orientation is not either horizontal or vertical.
            ValueError: If the provided min value is not convertible to float.
            ValueError: If the provided max value is not convertible to float.
            ValueError: If the provided opacity value is not convertible to float.
            ValueError: If cmap or palette is not provided.
        """

        import matplotlib  # pylint: disable=import-outside-toplevel
        import numpy  # pylint: disable=import-outside-toplevel

        if max_width is None:
            if orientation == "horizontal":
                max_width = "270px"
            else:
                max_width = "100px"

        if isinstance(vis_params, (list, tuple)):
            vis_params = {"palette": list(vis_params)}
        elif not vis_params:
            vis_params = {}

        if not isinstance(vis_params, dict):
            raise TypeError("The vis_params must be a dictionary.")

        if isinstance(kwargs.get("colors"), (list, tuple)):
            vis_params["palette"] = list(kwargs["colors"])

        width, height = self._get_dimensions(orientation, kwargs)

        vmin = vis_params.get("min", kwargs.pop("vmin", 0))
        try:
            vmin = float(vmin) 
        except ValueError as err:
            raise ValueError("The provided min value must be scalar type.")

        vmax = vis_params.get("max", kwargs.pop("mvax", 1))
        try:
            vmax = float(vmax) 
        except ValueError as err:
            raise ValueError("The provided max value must be scalar type.")

        alpha = vis_params.get("opacity", kwargs.pop("alpha", 1))
        try:
            alpha = float(alpha)
        except ValueError as err:
            raise ValueError("opacity or alpha value must be scalar type.")

        if "palette" in vis_params.keys():
            hexcodes = common.to_hex_colors(common.check_cmap(vis_params["palette"]))
            if discrete:
                cmap = matplotlib.colors.ListedColormap(hexcodes)
                linspace = numpy.linspace(vmin, vmax, cmap.N + 1)
                norm = matplotlib.colors.BoundaryNorm(linspace, cmap.N)
            else:
                cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
                    "custom", hexcodes, N=256
                )
                norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
        elif cmap:
            cmap = matplotlib.pyplot.get_cmap(cmap)
            norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
        else:
            raise ValueError(
                'cmap keyword or "palette" key in vis_params must be provided.'
            )

        fig, ax = matplotlib.pyplot.subplots(figsize=(width, height))
        cb = matplotlib.colorbar.ColorbarBase(
            ax,
            norm=norm,
            alpha=alpha,
            cmap=cmap,
            orientation=orientation,
            **kwargs,
        )

        label = label or vis_params.get("bands") or kwargs.pop("caption", None)
        if label:
            cb.set_label(label, fontsize=font_size)

        if axis_off:
            ax.set_axis_off()
        ax.tick_params(labelsize=font_size)

        # Set the background color to transparent.
        if transparent_bg:
            fig.patch.set_alpha(0.0)

        super().__init__(layout=ipywidgets.Layout(width=max_width))
        with self:
            self.outputs = ()
            matplotlib.pyplot.show()

    def _get_dimensions(self, orientation, kwargs):
        default_dims = {"horizontal": (3.0, 0.3), "vertical": (0.3, 3.0)}
        if orientation in default_dims:
            default = default_dims[orientation]
            return (
                kwargs.get("width", default[0]),
                kwargs.get("height", default[1]),
            )
        raise ValueError(
            f"orientation must be one of [{', '.join(default_dims.keys())}]."
        )


@Theme.apply
class Legend(ipywidgets.VBox):
    """A legend widget that can be added to the map."""

    ALLOWED_POSITIONS = ["topleft", "topright", "bottomleft", "bottomright"]
    DEFAULT_COLORS = ["#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3"]
    DEFAULT_KEYS = ["One", "Two", "Three", "Four", "etc"]
    DEFAULT_MAX_HEIGHT = "400px"
    DEFAULT_MAX_WIDTH = "300px"

    def __init__(
        self,
        title="Legend",
        legend_dict=None,
        keys=None,
        colors=None,
        position="bottomright",
        builtin_legend=None,
        add_header=True,
        widget_args={},
        **kwargs,
    ):
        """Adds a customized legend to the map.

         Args:
            title (str, optional): Title of the legend. Defaults to 'Legend'.
            legend_dict (dict, optional): A dictionary containing legend items
                as keys and color as values. If provided, keys and colors will
                be ignored. Defaults to None.
            keys (list, optional): A list of legend keys. Defaults to None.
            colors (list, optional): A list of legend colors. Defaults to None.
            position (str, optional): Position of the legend. Defaults to
                'bottomright'.
            builtin_legend (str, optional): Name of the builtin legend to add
                to the map. Defaults to None.
            add_header (bool, optional): Whether the legend can be closed or
                not. Defaults to True.
            widget_args (dict, optional): Additional arguments passed to the
                widget_template() function. Defaults to {}.

        Raises:
            TypeError: If the keys are not a list.
            TypeError: If the colors are not list.
            TypeError: If the colors are not a list of tuples.
            TypeError: If the legend_dict is not a dictionary.
            ValueError: If the legend template does not exist.
            ValueError: If a rgb value cannot to be converted to hex.
            ValueError: If the keys and colors are not the same length.
            ValueError: If the builtin_legend is not allowed.
            ValueError: If the position is not allowed.

        """
        import os  # pylint: disable=import-outside-toplevel
        from IPython.display import display  # pylint: disable=import-outside-toplevel
        import pkg_resources  # pylint: disable=import-outside-toplevel
        from .legends import builtin_legends  # pylint: disable=import-outside-toplevel

        pkg_dir = os.path.dirname(
            pkg_resources.resource_filename("geemap", "geemap.py")
        )
        legend_template = os.path.join(pkg_dir, "data/template/legend.html")

        if not os.path.exists(legend_template):
            raise ValueError("The legend template does not exist.")

        if "labels" in kwargs:
            keys = kwargs["labels"]
            kwargs.pop("labels")

        if keys is not None:
            if not isinstance(keys, list):
                raise TypeError("The legend keys must be a list.")
        else:
            keys = Legend.DEFAULT_KEYS

        if colors is not None:
            if not isinstance(colors, list):
                raise TypeError("The legend colors must be a list.")
            elif all(isinstance(item, tuple) for item in colors):
                colors = Legend.__convert_rgb_colors_to_hex(colors)
            elif all((item.startswith("#") and len(item) == 7) for item in colors):
                pass
            elif all((len(item) == 6) for item in colors):
                pass
            else:
                raise TypeError("The legend colors must be a list of tuples.")
        else:
            colors = Legend.DEFAULT_COLORS

        if len(keys) != len(colors):
            raise ValueError("The legend keys and colors must be the same length.")

        allowed_builtin_legends = builtin_legends.keys()
        if builtin_legend is not None:
            builtin_legend_allowed = Legend.__check_if_allowed(
                builtin_legend, "builtin legend", allowed_builtin_legends
            )
            if builtin_legend_allowed:
                legend_dict = builtin_legends[builtin_legend]
                keys = list(legend_dict.keys())
                colors = list(legend_dict.values())

        if legend_dict is not None:
            if not isinstance(legend_dict, dict):
                raise TypeError("The legend dict must be a dictionary.")
            else:
                keys = list(legend_dict.keys())
                colors = list(legend_dict.values())
                if all(isinstance(item, tuple) for item in colors):
                    colors = Legend.__convert_rgb_colors_to_hex(colors)

        Legend.__check_if_allowed(position, "position", Legend.ALLOWED_POSITIONS)

        header = []
        footer = []
        content = Legend.__create_legend_items(keys, colors)

        with open(legend_template) as f:
            lines = f.readlines()
            lines[3] = lines[3].replace("Legend", title)
            header = lines[:6]
            footer = lines[11:]

        legend_html = header + content + footer
        legend_text = "".join(legend_html)
        legend_output = ipywidgets.Output(layout=Legend.__create_layout(**kwargs))
        legend_widget = ipywidgets.HTML(value=legend_text)

        if add_header:
            if "show_close_button" not in widget_args:
                widget_args["show_close_button"] = False
            if "widget_icon" not in widget_args:
                widget_args["widget_icon"] = "bars"

            legend_output_widget = common.widget_template(
                legend_output,
                position=position,
                display_widget=legend_widget,
                **widget_args,
            )
        else:
            legend_output_widget = legend_widget

        super().__init__(children=[legend_output_widget])

        legend_output.clear_output()
        with legend_output:
            display(legend_widget)

    def __check_if_allowed(value, value_name, allowed_list):
        if value not in allowed_list:
            raise ValueError(
                "The "
                + value_name
                + " must be one of the following: {}.".format(", ".join(allowed_list))
            )
        return True

    def __convert_rgb_colors_to_hex(colors):
        try:
            return [common.rgb_to_hex(x) for x in colors]
        except:
            raise ValueError("Unable to convert rgb value to hex.")

    def __create_legend_items(keys, colors):
        legend_items = []
        for index, key in enumerate(keys):
            color = colors[index]
            if not color.startswith("#"):
                color = "#" + color
            item = "<li><span style='background:{};'></span>{}</li>\n".format(
                color, key
            )
            legend_items.append(item)
        return legend_items

    def __create_layout(**kwargs):
        height = Legend.__create_layout_property("height", None, **kwargs)

        min_height = Legend.__create_layout_property("min_height", None, **kwargs)

        if height is None:
            max_height = Legend.DEFAULT_MAX_HEIGHT
        else:
            max_height = Legend.__create_layout_property("max_height", None, **kwargs)

        width = Legend.__create_layout_property("width", None, **kwargs)

        if "min_width" not in kwargs:
            min_width = None

        if width is None:
            max_width = Legend.DEFAULT_MAX_WIDTH
        else:
            max_width = Legend.__create_layout_property(
                "max_width", Legend.DEFAULT_MAX_WIDTH, **kwargs
            )

        return {
            "height": height,
            "max_height": max_height,
            "max_width": max_width,
            "min_height": min_height,
            "min_width": min_width,
            "overflow": "scroll",
            "width": width,
        }

    def __create_layout_property(name, default_value, **kwargs):
        return default_value if name not in kwargs else kwargs[name]


@Theme.apply
class Inspector(ipywidgets.VBox):
    """Inspector widget for Earth Engine data."""

    def __init__(
        self,
        host_map,
        names=None,
        visible=True,
        decimals=2,
        opened=True,
        show_close_button=True,
    ):
        """Creates an Inspector widget for Earth Engine data.

        Args:
            host_map (geemap.Map): The map to add the inspector widget to.
            names (list, optional): The list of layer names to be inspected.
                Defaults to None.
            visible (bool, optional): Whether to inspect visible layers only.
                Defaults to True.
            decimals (int, optional): The number of decimal places to round the
                values. Defaults to 2.
            opened (bool, optional): Whether the inspector is opened. Defaults
                to True.
            show_close_button (bool, optional): Whether to show the close
                button. Defaults to True.
        """

        self._host_map = host_map
        if not host_map:
            raise ValueError("Must pass a valid map when creating an inspector.")

        self._names = names
        self._visible = visible
        self._decimals = decimals
        self._opened = opened

        self.on_close = None

        self._expand_point_tree = False
        self._expand_pixels_tree = True
        self._expand_objects_tree = False

        host_map.default_style = {"cursor": "crosshair"}

        left_padded_square = ipywidgets.Layout(
            width="28px", height="28px", padding="0px 0px 0px 4px"
        )

        self.toolbar_button = ipywidgets.ToggleButton(
            value=opened, tooltip="Inspector", icon="info", layout=left_padded_square
        )
        self.toolbar_button.observe(self._on_toolbar_btn_click, "value")

        close_button = ipywidgets.ToggleButton(
            value=False,
            tooltip="Close the tool",
            icon="times",
            button_style="primary",
            layout=left_padded_square,
        )
        close_button.observe(self._on_close_btn_click, "value")

        point_checkbox = self._create_checkbox("Point", self._expand_point_tree)
        pixels_checkbox = self._create_checkbox("Pixels", self._expand_pixels_tree)
        objects_checkbox = self._create_checkbox("Objects", self._expand_objects_tree)
        point_checkbox.observe(self._on_point_checkbox_changed, "value")
        pixels_checkbox.observe(self._on_pixels_checkbox_changed, "value")
        objects_checkbox.observe(self._on_objects_checkbox_changed, "value")
        self.inspector_checks = ipywidgets.HBox(
            children=[
                ipywidgets.Label(
                    "Expand", layout=ipywidgets.Layout(padding="0px 8px 0px 4px")
                ),
                point_checkbox,
                pixels_checkbox,
                objects_checkbox,
            ]
        )

        if show_close_button:
            self.toolbar_header = ipywidgets.HBox(
                children=[close_button, self.toolbar_button]
            )
        else:
            self.toolbar_header = ipywidgets.HBox(children=[self.toolbar_button])
        self.tree_output = ipywidgets.VBox(
            children=[],
            layout=ipywidgets.Layout(
                max_width="600px", max_height="300px", overflow="auto", display="block"
            ),
        )
        self._clear_inspector_output()

        host_map.on_interaction(self._on_map_interaction)
        self.toolbar_button.value = opened

        super().__init__(
            children=[self.toolbar_header, self.inspector_checks, self.tree_output]
        )

    def cleanup(self):
        """Removes the widget from the map and performs cleanup."""
        if self._host_map:
            self._host_map.default_style = {"cursor": "default"}
            self._host_map.on_interaction(self._on_map_interaction, remove=True)
        if self.on_close is not None:
            self.on_close()

    def _create_checkbox(self, title, checked):
        layout = ipywidgets.Layout(width="auto", padding="0px 6px 0px 0px")
        return ipywidgets.Checkbox(
            description=title, indent=False, value=checked, layout=layout
        )

    def _on_map_interaction(self, **kwargs):
        latlon = kwargs.get("coordinates")
        if kwargs.get("type") == "click":
            self._on_map_click(latlon)

    def _on_map_click(self, latlon):
        if self.toolbar_button.value:
            self._host_map.default_style = {"cursor": "wait"}
            self._clear_inspector_output()

            nodes = [self._point_info(latlon)]
            pixels_node = self._pixels_info(latlon)
            if pixels_node.nodes:
                nodes.append(pixels_node)
            objects_node = self._objects_info(latlon)
            if objects_node.nodes:
                nodes.append(objects_node)

            self.tree_output.children = [ipytree.Tree(nodes=nodes)]
            self._host_map.default_style = {"cursor": "crosshair"}

    def _clear_inspector_output(self):
        self.tree_output.children = []
        self.children = []
        self.children = [self.toolbar_header, self.inspector_checks, self.tree_output]

    def _on_point_checkbox_changed(self, change):
        self._expand_point_tree = change["new"]

    def _on_pixels_checkbox_changed(self, change):
        self._expand_pixels_tree = change["new"]

    def _on_objects_checkbox_changed(self, change):
        self._expand_objects_tree = change["new"]

    def _on_toolbar_btn_click(self, change):
        if change["new"]:
            self._host_map.default_style = {"cursor": "crosshair"}
            self.children = [
                self.toolbar_header,
                self.inspector_checks,
                self.tree_output,
            ]
            self._clear_inspector_output()
        else:
            self.children = [self.toolbar_button]
            self._host_map.default_style = {"cursor": "default"}

    def _on_close_btn_click(self, change):
        if change["new"]:
            self.cleanup()

    def _get_visible_map_layers(self):
        layers = {}
        if self._names is not None:
            names = [names] if isinstance(names, str) else self._names
            for name in names:
                if name in self._host_map.ee_layers:
                    layers[name] = self._host_map.ee_layers[name]
        else:
            layers = self._host_map.ee_layers
        return {k: v for k, v in layers.items() if v["ee_layer"].visible}

    def _root_node(self, title, nodes, **kwargs):
        return ipytree.Node(
            title,
            icon="archive",
            nodes=nodes,
            open_icon="plus-square",
            open_icon_style="success",
            close_icon="minus-square",
            close_icon_style="info",
            **kwargs,
        )

    def _point_info(self, latlon):
        scale = self._host_map.get_scale()
        label = (
            f"Point ({latlon[1]:.{self._decimals}f}, "
            + f"{latlon[0]:.{self._decimals}f}) at {int(scale)}m/px"
        )
        nodes = [
            ipytree.Node(f"Longitude: {latlon[1]}"),
            ipytree.Node(f"Latitude: {latlon[0]}"),
            ipytree.Node(f"Zoom Level: {self._host_map.zoom}"),
            ipytree.Node(f"Scale (approx. m/px): {scale}"),
        ]
        return self._root_node(label, nodes, opened=self._expand_point_tree)

    def _query_point(self, latlon, ee_object):
        point = ee.Geometry.Point(latlon[::-1])
        scale = self._host_map.get_scale()
        if isinstance(ee_object, ee.ImageCollection):
            ee_object = ee_object.mosaic()
        if isinstance(ee_object, ee.Image):
            return ee_object.reduceRegion(ee.Reducer.first(), point, scale).getInfo()
        return None

    def _pixels_info(self, latlon):
        if not self._visible:
            return self._root_node("Pixels", [])

        layers = self._get_visible_map_layers()
        nodes = []
        for layer_name, layer in layers.items():
            ee_object = layer["ee_object"]
            pixel = self._query_point(latlon, ee_object)
            if not pixel:
                continue
            pluralized_band = "band" if len(pixel) == 1 else "bands"
            ee_obj_type = ee_object.__class__.__name__
            label = f"{layer_name}: {ee_obj_type} ({len(pixel)} {pluralized_band})"
            layer_node = ipytree.Node(label, opened=self._expand_pixels_tree)
            for key, value in sorted(pixel.items()):
                if isinstance(value, float):
                    value = round(value, self._decimals)
                layer_node.add_node(ipytree.Node(f"{key}: {value}", icon="file"))
            nodes.append(layer_node)

        return self._root_node("Pixels", nodes)

    def _get_bbox(self, latlon):
        lat, lon = latlon
        delta = 0.005
        return ee.Geometry.BBox(lon - delta, lat - delta, lon + delta, lat + delta)

    def _objects_info(self, latlon):
        if not self._visible:
            return self._root_node("Objects", [])

        layers = self._get_visible_map_layers()
        point = ee.Geometry.Point(latlon[::-1])
        nodes = []
        for layer_name, layer in layers.items():
            ee_object = layer["ee_object"]
            if isinstance(ee_object, ee.FeatureCollection):
                geom = ee.Feature(ee_object.first()).geometry()
                bbox = self._get_bbox(latlon)
                is_point = ee.Algorithms.If(
                    geom.type().compareTo(ee.String("Point")), point, bbox
                )
                ee_object = ee_object.filterBounds(is_point).first()
                tree_node = common.get_info(
                    ee_object, layer_name, self._expand_objects_tree, True
                )
                if tree_node:
                    nodes.append(tree_node)

        return self._root_node("Objects", nodes)


@Theme.apply
class LayerManager(ipywidgets.VBox):
    def __init__(self, host_map):
        """Initializes a layer manager widget.
        Args:
            host_map (geemap.Map): The geemap.Map object.
        """
        self._host_map = host_map
        if not host_map:
            raise ValueError("Must pass a valid map when creating a layer manager.")

        self._collapse_button = ipywidgets.ToggleButton(
            value=False,
            tooltip="Layer Manager",
            icon="server",
            layout=ipywidgets.Layout(
                width="28px", height="28px", padding="0px 0px 0px 4px"
            ),
        )
        self._close_button = ipywidgets.Button(
            tooltip="Close the tool",
            icon="times",
            button_style="primary",
            layout=ipywidgets.Layout(width="28px", height="28px", padding="0px"),
        )

        self._toolbar_header = ipywidgets.HBox(
            children=[self._close_button, self._collapse_button]
        )
        self._toolbar_footer = ipywidgets.VBox(children=[])

        self._collapse_button.observe(self._on_collapse_click, "value")
        self._close_button.on_click(self._on_close_click)

        self.on_close = None
        self.on_open_vis = None

        self.collapsed = False
        self.header_hidden = False
        self.close_button_hidden = False

        super().__init__([self._toolbar_header, self._toolbar_footer])

    @property
    def collapsed(self):
        return not self._collapse_button.value

    @collapsed.setter
    def collapsed(self, value):
        self._collapse_button.value = not value

    @property
    def header_hidden(self):
        return self._toolbar_header.layout.display == "none"

    @header_hidden.setter
    def header_hidden(self, value):
        self._toolbar_header.layout.display = "none" if value else "block"

    @property
    def close_button_hidden(self):
        return self._close_button.style.display == "none"

    @close_button_hidden.setter
    def close_button_hidden(self, value):
        self._close_button.style.display = "none" if value else "inline-block"

    def refresh_layers(self):
        """Recreates all the layer widgets."""
        toggle_all_layout = ipywidgets.Layout(
            height="18px", width="30ex", padding="0px 8px 25px 8px"
        )
        toggle_all_checkbox = ipywidgets.Checkbox(
            value=False,
            description="All layers on/off",
            indent=False,
            layout=toggle_all_layout,
        )
        toggle_all_checkbox.observe(self._on_all_layers_visibility_toggled, "value")

        layer_rows = []
        # non_basemap_layers = self._host_map.layers[1:]  # Skip the basemap.
        for layer in self._host_map.layers:
            layer_rows.append(self._render_layer_row(layer))
        self._toolbar_footer.children = [toggle_all_checkbox] + layer_rows

    def _on_close_click(self, _):
        if self.on_close:
            self.on_close()

    def _on_collapse_click(self, change):
        if change["new"]:
            self.refresh_layers()
            self.children = [self._toolbar_header, self._toolbar_footer]
        else:
            self.children = [self._collapse_button]

    def _render_layer_row(self, layer):
        visibility_checkbox = ipywidgets.Checkbox(
            value=self._compute_layer_visibility(layer),
            description=layer.name,
            indent=False,
            layout=ipywidgets.Layout(height="18px", width="140px"),
        )
        visibility_checkbox.observe(
            lambda change: self._on_layer_visibility_changed(change, layer), "value"
        )

        opacity_slider = ipywidgets.FloatSlider(
            value=self._compute_layer_opacity(layer),
            min=0,
            max=1,
            step=0.01,
            readout=False,
            layout=ipywidgets.Layout(width="80px"),
        )
        opacity_slider.observe(
            lambda change: self._on_layer_opacity_changed(change, layer), "value"
        )

        settings_button = ipywidgets.Button(
            icon="gear",
            layout=ipywidgets.Layout(width="25px", height="25px", padding="0px"),
            tooltip=layer.name,
        )
        settings_button.on_click(self._on_layer_settings_click)

        return ipywidgets.HBox(
            [visibility_checkbox, settings_button, opacity_slider],
            layout=ipywidgets.Layout(padding="0px 8px 0px 8px"),
        )

    def _compute_layer_opacity(self, layer):
        if layer in self._host_map.geojson_layers:
            opacity = layer.style.get("opacity", 1.0)
            fill_opacity = layer.style.get("fillOpacity", 1.0)
            return max(opacity, fill_opacity)
        return layer.opacity if hasattr(layer, "opacity") else 1.0

    def _compute_layer_visibility(self, layer):
        return layer.visible if hasattr(layer, "visible") else True

    def _on_layer_settings_click(self, button):
        if self.on_open_vis:
            self.on_open_vis(button.tooltip)

    def _on_all_layers_visibility_toggled(self, change):
        checkboxes = [
            row.children[0] for row in self._toolbar_footer.children[1:]
        ]  # Skip the all on/off checkbox.
        for checkbox in checkboxes:
            checkbox.value = change["new"]

    def _on_layer_opacity_changed(self, change, layer):
        if layer in self._host_map.geojson_layers:
            # For non-TileLayer, use layer.style.opacity and layer.style.fillOpacity.
            layer.style.update({"opacity": change["new"], "fillOpacity": change["new"]})
        elif hasattr(layer, "opacity"):
            layer.opacity = change["new"]

    def _on_layer_visibility_changed(self, change, layer):
        if hasattr(layer, "visible"):
            layer.visible = change["new"]

        layer_name = change["owner"].description
        if layer_name not in self._host_map.ee_layers:
            return

        layer_dict = self._host_map.ee_layers[layer_name]
        for attachment_name in ["legend", "colorbar"]:
            attachment = layer_dict.get(attachment_name, None)
            attachment_on_map = attachment in self._host_map.controls
            if change["new"] and not attachment_on_map:
                try:
                    self._host_map.add(attachment)
                except:
                    from ipyleaflet import WidgetControl
                    widget = attachment.widget
                    position = attachment.position
                    control = WidgetControl(widget=widget, position=position)
                    self._host_map.add(control)
                    layer_dict["colorbar"] = control

                    
            elif not change["new"] and attachment_on_map:
                self._host_map.remove_control(attachment)


@Theme.apply
class Basemap(ipywidgets.HBox):
    """Widget for selecting a basemap."""

    def __init__(self, basemaps, value):
        """Creates a widget for selecting a basemap.

        Args:
            basemaps (list): The list of basemap names to make available for selection.
            value (str): The default value from basemaps to select.
        """
        self.on_close = None
        self.on_basemap_changed = None

        self._dropdown = ipywidgets.Dropdown(
            options=list(basemaps),
            value=value,
            layout=ipywidgets.Layout(width="200px"),
        )
        self._dropdown.observe(self._on_dropdown_click, "value")

        close_button = ipywidgets.Button(
            icon="times",
            tooltip="Close the basemap widget",
            button_style="primary",
            layout=ipywidgets.Layout(width="32px"),
        )
        close_button.on_click(self._on_close_click)

        super().__init__([self._dropdown, close_button])

    def _on_dropdown_click(self, change):
        if self.on_basemap_changed and change["new"]:
            self.on_basemap_changed(self._dropdown.value)

    def cleanup(self):
        if self.on_close:
            self.on_close()

    def _on_close_click(self, _):
        self.cleanup()


@Theme.apply
class LayerEditor(ipywidgets.VBox):
    """Widget for displaying and editing layer visualization properties."""

    def __init__(self, host_map, layer_dict):
        """Initializes a layer editor widget.

        Args:
            host_map (geemap.Map): The geemap.Map object.
            layer_dict (dict): The layer object to edit.
        """

        self.on_close = None

        self._host_map = host_map
        if not host_map:
            raise ValueError(
                f"Must pass a valid map when creating a {self.__class__.__name__} widget."
            )

        self._toggle_button = ipywidgets.ToggleButton(
            value=True,
            tooltip="Layer editor",
            icon="gear",
            layout=ipywidgets.Layout(
                width="28px", height="28px", padding="0px 0 0 3px"
            ),
        )
        self._toggle_button.observe(self._on_toggle_click, "value")

        self._close_button = ipywidgets.Button(
            tooltip="Close the vis params dialog",
            icon="times",
            button_style="primary",
            layout=ipywidgets.Layout(width="28px", height="28px", padding="0"),
        )
        self._close_button.on_click(self._on_close_click)

        layout = ipywidgets.Layout(width="95px")
        self._import_button = ipywidgets.Button(
            description="Import",
            button_style="primary",
            tooltip="Import vis params to notebook",
            layout=layout,
        )
        self._apply_button = ipywidgets.Button(
            description="Apply", tooltip="Apply vis params to the layer", layout=layout
        )
        self._import_button.on_click(self._on_import_click)
        self._apply_button.on_click(self._on_apply_click)

        self._label = ipywidgets.Label(
            value="Layer name",
            layout=ipywidgets.Layout(max_width="250px", padding="1px 8px 0 4px"),
        )
        self._embedded_widget = ipywidgets.Label(value="Vis params are uneditable")
        if layer_dict is not None:
            self._ee_object = layer_dict["ee_object"]
            if isinstance(self._ee_object, (ee.Feature, ee.Geometry)):
                self._ee_object = ee.FeatureCollection(self._ee_object)

            self._ee_layer = layer_dict["ee_layer"]
            self._label.value = self._ee_layer.name
            if isinstance(self._ee_object, ee.FeatureCollection):
                self._embedded_widget = _VectorLayerEditor(
                    host_map=host_map, layer_dict=layer_dict
                )
            elif isinstance(self._ee_object, ee.Image):
                self._embedded_widget = _RasterLayerEditor(
                    host_map=host_map, layer_dict=layer_dict
                )

        super().__init__(children=[])
        self._on_toggle_click({"new": True})

    def _on_toggle_click(self, change):
        if change["new"]:
            self.children = [
                ipywidgets.HBox([self._close_button, self._toggle_button, self._label]),
                self._embedded_widget,
                ipywidgets.HBox([self._import_button, self._apply_button]),
            ]
        else:
            self.children = [
                ipywidgets.HBox([self._close_button, self._toggle_button, self._label]),
            ]

    def _on_import_click(self, _):
        self._embedded_widget.on_import_click()

    def _on_apply_click(self, _):
        self._embedded_widget.on_apply_click()

    def _on_close_click(self, _):
        if self.on_close:
            self.on_close()


@Theme.apply
class _RasterLayerEditor(ipywidgets.VBox):
    """Widget for displaying and editing layer visualization properties for raster layers."""

    def __init__(self, host_map, layer_dict):
        """Initializes a raster layer editor widget.

        Args:
            host_map (geemap.Map): The geemap.Map object.
            layer_dict (dict): The layer object to edit.
        """
        self._host_map = host_map
        self._layer_dict = layer_dict

        self._ee_object = layer_dict["ee_object"]
        self._ee_layer = layer_dict["ee_layer"]
        self._vis_params = layer_dict["vis_params"]

        self._layer_name = self._ee_layer.name
        self._layer_opacity = self._ee_layer.opacity

        self._min_value = 0
        self._max_value = 100
        self._sel_bands = None
        self._layer_palette = []
        self._layer_gamma = 1
        self._left_value = 0
        self._right_value = 10000

        band_names = self._ee_object.bandNames().getInfo()
        self._band_count = len(band_names)

        if "min" in self._vis_params.keys():
            self._min_value = self._vis_params["min"]
            if self._min_value < self._left_value:
                self._left_value = self._min_value - self._max_value
        if "max" in self._vis_params.keys():
            self._max_value = self._vis_params["max"]
            self._right_value = 2 * self._max_value
        if "gamma" in self._vis_params.keys():
            if isinstance(self._vis_params["gamma"], list):
                self._layer_gamma = self._vis_params["gamma"][0]
            else:
                self._layer_gamma = self._vis_params["gamma"]
        if "bands" in self._vis_params.keys():
            self._sel_bands = self._vis_params["bands"]
        if "palette" in self._vis_params.keys():
            self._layer_palette = [
                color.replace("#", "") for color in list(self._vis_params["palette"])
            ]

        # ipywidgets doesn't support horizontal radio buttons
        # (https://github.com/jupyter-widgets/ipywidgets/issues/1247). Instead,
        # use two individual radio buttons with some hackery.
        self._greyscale_radio_button = ipywidgets.RadioButtons(
            options=["1 band (Grayscale)"],
            layout={"width": "max-content", "margin": "0 15px 0 0"},
        )
        self._rgb_radio_button = ipywidgets.RadioButtons(
            options=["3 bands (RGB)"], layout={"width": "max-content"}
        )
        self._greyscale_radio_button.index = None
        self._rgb_radio_button.index = None

        band_dropdown_layout = ipywidgets.Layout(width="98px")
        self._band_1_dropdown = ipywidgets.Dropdown(
            options=band_names, value=band_names[0], layout=band_dropdown_layout
        )
        self._band_2_dropdown = ipywidgets.Dropdown(
            options=band_names, value=band_names[0], layout=band_dropdown_layout
        )
        self._band_3_dropdown = ipywidgets.Dropdown(
            options=band_names, value=band_names[0], layout=band_dropdown_layout
        )
        self._bands_hbox = ipywidgets.HBox(layout=ipywidgets.Layout(margin="0 0 6px 0"))

        self._color_picker = ipywidgets.ColorPicker(
            concise=False,
            value="#000000",
            layout=ipywidgets.Layout(width="116px"),
            style={"description_width": "initial"},
        )

        self._add_color_button = ipywidgets.Button(
            icon="plus",
            tooltip="Add a hex color string to the palette",
            layout=ipywidgets.Layout(width="32px"),
        )
        self._del_color_button = ipywidgets.Button(
            icon="minus",
            tooltip="Remove a hex color string from the palette",
            layout=ipywidgets.Layout(width="32px"),
        )
        self._reset_color_button = ipywidgets.Button(
            icon="eraser",
            tooltip="Remove all color strings from the palette",
            layout=ipywidgets.Layout(width="34px"),
        )
        self._add_color_button.on_click(self._add_color_clicked)
        self._del_color_button.on_click(self._del_color_clicked)
        self._reset_color_button.on_click(self._reset_color_clicked)

        self._classes_dropdown = ipywidgets.Dropdown(
            options=["Any"] + [str(i) for i in range(3, 13)],
            description="Classes:",
            layout=ipywidgets.Layout(width="115px"),
            style={"description_width": "initial"},
        )
        self._classes_dropdown.observe(self._classes_changed, "value")

        self._colormap_dropdown = ipywidgets.Dropdown(
            options=self._get_colormaps(),
            value=None,
            description="Colormap:",
            layout=ipywidgets.Layout(width="181px"),
            style={"description_width": "initial"},
        )
        self._colormap_dropdown.observe(self._colormap_changed, "value")

        self._palette_label = ipywidgets.Text(
            value=", ".join(self._layer_palette),
            placeholder="List of hex color code (RRGGBB)",
            description="Palette:",
            tooltip="Enter a list of hex color code (RRGGBB)",
            layout=ipywidgets.Layout(width="300px"),
            style={"description_width": "initial"},
        )

        self._stretch_dropdown = ipywidgets.Dropdown(
            options={
                "Custom": {},
                "1 σ": {"sigma": 1},
                "2 σ": {"sigma": 2},
                "3 σ": {"sigma": 3},
                "90%": {"percent": 0.90},
                "98%": {"percent": 0.98},
                "100%": {"percent": 1.0},
            },
            description="Stretch:",
            layout=ipywidgets.Layout(width="260px"),
            style={"description_width": "initial"},
        )

        self._stretch_button = ipywidgets.Button(
            disabled=True,
            tooltip="Re-calculate stretch",
            layout=ipywidgets.Layout(width="36px"),
            icon="refresh",
        )
        self._stretch_dropdown.observe(self._value_stretch_changed, names="value")
        self._stretch_button.on_click(self._update_stretch)

        self._value_range_slider = ipywidgets.FloatRangeSlider(
            value=[self._min_value, self._max_value],
            min=self._left_value,
            max=self._right_value,
            step=0.1,
            description="Range:",
            disabled=False,
            continuous_update=False,
            readout=True,
            readout_format=".1f",
            layout=ipywidgets.Layout(width="300px"),
            style={"description_width": "45px"},
        )

        self._opacity_slider = ipywidgets.FloatSlider(
            value=self._layer_opacity,
            min=0,
            max=1,
            step=0.01,
            description="Opacity:",
            continuous_update=False,
            readout=True,
            readout_format=".2f",
            layout=ipywidgets.Layout(width="320px"),
            style={"description_width": "50px"},
        )

        self._gamma_slider = ipywidgets.FloatSlider(
            value=self._layer_gamma,
            min=0.1,
            max=10,
            step=0.01,
            description="Gamma:",
            continuous_update=False,
            readout=True,
            readout_format=".2f",
            layout=ipywidgets.Layout(width="320px"),
            style={"description_width": "50px"},
        )

        self._legend_checkbox = ipywidgets.Checkbox(
            value=False,
            description="Legend",
            indent=False,
            layout=ipywidgets.Layout(width="70px"),
        )

        self._linear_checkbox = ipywidgets.Checkbox(
            value=True,
            description="Linear colormap",
            indent=False,
            layout=ipywidgets.Layout(width="150px"),
        )
        self._step_checkbox = ipywidgets.Checkbox(
            value=False,
            description="Step colormap",
            indent=False,
            layout=ipywidgets.Layout(width="140px"),
        )
        self._linear_checkbox.observe(self._linear_checkbox_changed, "value")
        self._step_checkbox.observe(self._step_checkbox_changed, "value")

        self._legend_title_label = ipywidgets.Text(
            value="Legend",
            description="Legend title:",
            tooltip="Enter a title for the legend",
            layout=ipywidgets.Layout(width="300px"),
            style={"description_width": "initial"},
        )

        self._legend_labels_label = ipywidgets.Text(
            value="Class 1, Class 2, Class 3",
            description="Legend labels:",
            tooltip="Enter a a list of labels for the legend",
            layout=ipywidgets.Layout(width="300px"),
            style={"description_width": "initial"},
        )

        self._stretch_hbox = ipywidgets.HBox(
            [self._stretch_dropdown, self._stretch_button]
        )
        self._colormap_hbox = ipywidgets.HBox(
            [self._linear_checkbox, self._step_checkbox]
        )
        self._legend_vbox = ipywidgets.VBox()

        self._colorbar_output = ipywidgets.Output(
            layout=ipywidgets.Layout(height="60px", max_width="300px")
        )

        self._legend_checkbox.observe(self._legend_checkbox_changed, "value")

        children = []
        if self._band_count < 3:
            self._greyscale_radio_button.index = 0
            self._band_1_dropdown.layout.width = "300px"
            self._bands_hbox.children = [self._band_1_dropdown]
            children = self._get_tool_layout(grayscale=True)
            self._legend_checkbox.value = False

            if len(self._palette_label.value) > 0 and "," in self._palette_label.value:
                colors = common.to_hex_colors(
                    [color.strip() for color in self._palette_label.value.split(",")]
                )
                self._render_colorbar(colors)
        else:
            self._rgb_radio_button.index = 0
            sel_bands = self._sel_bands
            if (sel_bands is None) or (len(sel_bands) < 2):
                sel_bands = band_names[0:3]
            self._band_1_dropdown.value = sel_bands[0]
            self._band_2_dropdown.value = sel_bands[1]
            self._band_3_dropdown.value = sel_bands[2]
            self._bands_hbox.children = [
                self._band_1_dropdown,
                self._band_2_dropdown,
                self._band_3_dropdown,
            ]
            children = self._get_tool_layout(grayscale=False)

        self._greyscale_radio_button.observe(self._radio1_observer, names=["value"])
        self._rgb_radio_button.observe(self._radio2_observer, names=["value"])

        super().__init__(
            layout=ipywidgets.Layout(
                padding="5px 0px 5px 8px",  # top, right, bottom, left
                # width="330px",
                max_height="305px",
                overflow="auto",
                display="block",
            ),
            children=children,
        )

    def _value_stretch_changed(self, value):
        """Apply the selected stretch option and update widget states."""
        stretch_option = value["new"]

        if stretch_option:
            self._stretch_button.disabled = False
            self._value_range_slider.disabled = True
            self._update_stretch()
        else:
            self._stretch_button.disabled = True
            self._value_range_slider.disabled = False

    def _update_stretch(self, *_):
        """Calculate and set the range slider by applying stretch parameters."""
        stretch_params = self._stretch_dropdown.value

        (s, w), (n, e) = self._host_map.bounds
        map_bbox = ee.Geometry.BBox(west=w, south=s, east=e, north=n)
        vis_bands = set((b.value for b in self._bands_hbox.children))
        min_val, max_val = self._ee_layer.calculate_vis_minmax(
            bounds=map_bbox,
            bands=vis_bands,
            **stretch_params
        )

        # Update in the correct order to avoid setting an invalid range
        if min_val > self._value_range_slider.max:
            self._value_range_slider.max = max_val
            self._value_range_slider.min = min_val
        else:
            self._value_range_slider.min = min_val
            self._value_range_slider.max = max_val

        self._value_range_slider.value = [min_val, max_val]

    def _get_tool_layout(self, grayscale):
        return [
            ipywidgets.HBox([self._greyscale_radio_button, self._rgb_radio_button]),
            self._bands_hbox,
            self._stretch_hbox,
            self._value_range_slider,
            self._opacity_slider,
            self._gamma_slider,
        ] + (
            [
                ipywidgets.HBox([self._classes_dropdown, self._colormap_dropdown]),
                self._palette_label,
                self._colorbar_output,
                ipywidgets.HBox(
                    [
                        self._legend_checkbox,
                        self._color_picker,
                        self._add_color_button,
                        self._del_color_button,
                        self._reset_color_button,
                    ]
                ),
                self._legend_vbox,
            ]
            if grayscale
            else []
        )

    def _get_colormaps(self):
        from matplotlib import pyplot  # pylint: disable=import-outside-toplevel

        colormap_options = pyplot.colormaps()
        colormap_options.sort()
        return colormap_options

    def _render_colorbar(self, colors):
        import matplotlib  # pylint: disable=import-outside-toplevel
        from matplotlib import pyplot  # pylint: disable=import-outside-toplevel

        colors = common.to_hex_colors(colors)

        _, ax = pyplot.subplots(figsize=(4, 0.3))
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
            "custom", colors, N=256
        )
        norm = matplotlib.colors.Normalize(
            vmin=self._value_range_slider.value[0],
            vmax=self._value_range_slider.value[1],
        )
        matplotlib.colorbar.ColorbarBase(
            ax, norm=norm, cmap=cmap, orientation="horizontal"
        )

        self._palette_label.value = ", ".join(colors)

        self._colorbar_output.clear_output()
        with self._colorbar_output:
            pyplot.show()

    def _classes_changed(self, change):
        import matplotlib  # pylint: disable=import-outside-toplevel
        from matplotlib import pyplot  # pylint: disable=import-outside-toplevel

        if not change["new"]:
            return

        selected = change["owner"].value
        if self._colormap_dropdown.value is not None:
            n_class = None
            if selected != "Any":
                n_class = int(self._classes_dropdown.value)

            colors = pyplot.cm.get_cmap(self._colormap_dropdown.value, n_class)
            cmap_colors = [
                matplotlib.colors.rgb2hex(colors(i))[1:] for i in range(colors.N)
            ]
            self._render_colorbar(cmap_colors)

            if len(self._palette_label.value) > 0 and "," in self._palette_label.value:
                labels = [
                    f"Class {i+1}"
                    for i in range(len(self._palette_label.value.split(",")))
                ]
                self._legend_labels_label.value = ", ".join(labels)

    def _add_color_clicked(self, _):
        if self._color_picker.value is not None:
            if len(self._palette_label.value) == 0:
                self._palette_label.value = self._color_picker.value[1:]
            else:
                self._palette_label.value += ", " + self._color_picker.value[1:]

    def _del_color_clicked(self, _):
        if "," in self._palette_label.value:
            items = [item.strip() for item in self._palette_label.value.split(",")]
            self._palette_label.value = ", ".join(items[:-1])
        else:
            self._palette_label.value = ""

    def _reset_color_clicked(self, _):
        self._palette_label.value = ""

    def _linear_checkbox_changed(self, change):
        if change["new"]:
            self._step_checkbox.value = False
            self._legend_vbox.children = [self._colormap_hbox]
        else:
            self._step_checkbox.value = True

    def _step_checkbox_changed(self, change):
        if change["new"]:
            self._linear_checkbox.value = False
            if len(self._layer_palette) > 0:
                self._legend_labels_label.value = ",".join(
                    ["Class " + str(i) for i in range(1, len(self._layer_palette) + 1)]
                )
            self._legend_vbox.children = [
                self._colormap_hbox,
                self._legend_title_label,
                self._legend_labels_label,
            ]
        else:
            self._linear_checkbox.value = True

    def _colormap_changed(self, change):
        import matplotlib  # pylint: disable=import-outside-toplevel
        from matplotlib import pyplot  # pylint: disable=import-outside-toplevel

        if change["new"]:
            n_class = None
            if self._classes_dropdown.value != "Any":
                n_class = int(self._classes_dropdown.value)

            colors = pyplot.cm.get_cmap(self._colormap_dropdown.value, n_class)
            cmap_colors = [
                matplotlib.colors.rgb2hex(colors(i))[1:] for i in range(colors.N)
            ]
            self._render_colorbar(cmap_colors)

            if len(self._palette_label.value) > 0 and "," in self._palette_label.value:
                labels = [
                    f"Class {i+1}"
                    for i in range(len(self._palette_label.value.split(",")))
                ]
                self._legend_labels_label.value = ", ".join(labels)

    def on_import_click(self):
        vis = {}
        if self._greyscale_radio_button.index == 0:
            vis["bands"] = [self._band_1_dropdown.value]
            if len(self._palette_label.value) > 0:
                vis["palette"] = self._palette_label.value.split(",")
        else:
            vis["bands"] = [
                self._band_1_dropdown.value,
                self._band_2_dropdown.value,
                self._band_3_dropdown.value,
            ]

        vis["min"] = self._value_range_slider.value[0]
        vis["max"] = self._value_range_slider.value[1]
        vis["opacity"] = self._opacity_slider.value
        vis["gamma"] = self._gamma_slider.value

        common.create_code_cell(f"vis_params = {str(vis)}")
        print(f"vis_params = {str(vis)}")

    def on_apply_click(self):
        vis = {}
        if self._greyscale_radio_button.index == 0:
            vis["bands"] = [self._band_1_dropdown.value]
            if len(self._palette_label.value) > 0:
                vis["palette"] = [
                    c.strip() for c in self._palette_label.value.split(",")
                ]
        else:
            vis["bands"] = [
                self._band_1_dropdown.value,
                self._band_2_dropdown.value,
                self._band_3_dropdown.value,
            ]
            vis["gamma"] = self._gamma_slider.value

        vis["min"] = self._value_range_slider.value[0]
        vis["max"] = self._value_range_slider.value[1]

        self._host_map.add_layer(
            self._ee_object, vis, self._layer_name, True, self._opacity_slider.value
        )
        self._ee_layer.visible = False

        def _remove_control(key):
            if widget := self._layer_dict.get(key, None):
                if widget in self._host_map.controls:
                    self._host_map.remove(widget)
                del self._layer_dict[key]

        if self._legend_checkbox.value:
            _remove_control("colorbar")
            if self._linear_checkbox.value:
                _remove_control("legend")

                if (
                    len(self._palette_label.value) > 0
                    and "," in self._palette_label.value
                ):
                    colors = common.to_hex_colors(
                        [
                            color.strip()
                            for color in self._palette_label.value.split(",")
                        ]
                    )

                    if hasattr(self._host_map, "colorbar"):
                        self._host_map.add_colorbar(
                            vis_params={
                                "palette": colors,
                                "min": self._value_range_slider.value[0],
                                "max": self._value_range_slider.value[1],
                            },
                            layer_name=self._layer_name,
                        )
            elif self._step_checkbox.value:
                if (
                    len(self._palette_label.value) > 0
                    and "," in self._palette_label.value
                ):
                    colors = common.to_hex_colors(
                        [
                            color.strip()
                            for color in self._palette_label.value.split(",")
                        ]
                    )
                    labels = [
                        label.strip()
                        for label in self._legend_labels_label.value.split(",")
                    ]

                    if hasattr(self._host_map, "add_legend"):
                        self._host_map.add_legend(
                            title=self._legend_title_label.value,
                            legend_keys=labels,
                            legend_colors=colors,
                            layer_name=self._layer_name,
                        )
        else:
            if self._greyscale_radio_button.index == 0 and "palette" in vis:
                self._render_colorbar(vis["palette"])
                _remove_control("colorbar")
                _remove_control("legend")

    def _legend_checkbox_changed(self, change):
        if change["new"]:
            self._linear_checkbox.value = True
            self._legend_vbox.children = [
                ipywidgets.HBox([self._linear_checkbox, self._step_checkbox]),
            ]
        else:
            self._legend_vbox.children = []

    def _radio1_observer(self, _):
        self._rgb_radio_button.unobserve(self._radio2_observer, names=["value"])
        self._rgb_radio_button.index = None
        self._rgb_radio_button.observe(self._radio2_observer, names=["value"])
        self._band_1_dropdown.layout.width = "300px"
        self._bands_hbox.children = [self._band_1_dropdown]
        self._palette_label.value = ", ".join(self._layer_palette)
        self._palette_label.disabled = False
        self._color_picker.disabled = False
        self._add_color_button.disabled = False
        self._del_color_button.disabled = False
        self._reset_color_button.disabled = False
        self.children = self._get_tool_layout(grayscale=True)

        if len(self._palette_label.value) > 0 and "," in self._palette_label.value:
            colors = [color.strip() for color in self._palette_label.value.split(",")]
            self._render_colorbar(colors)

    def _radio2_observer(self, _):
        dropdown_width = "98px"
        self._greyscale_radio_button.unobserve(self._radio1_observer, names=["value"])
        self._greyscale_radio_button.index = None
        self._greyscale_radio_button.observe(self._radio1_observer, names=["value"])
        self._band_1_dropdown.layout.width = dropdown_width
        self._bands_hbox.children = [
            self._band_1_dropdown,
            self._band_2_dropdown,
            self._band_3_dropdown,
        ]
        self._palette_label.value = ""
        self._palette_label.disabled = True
        self._color_picker.disabled = True
        self._add_color_button.disabled = True
        self._del_color_button.disabled = True
        self._reset_color_button.disabled = True
        self.children = self._get_tool_layout(grayscale=False)
        self._colorbar_output.clear_output()


@Theme.apply
class _VectorLayerEditor(ipywidgets.VBox):
    """Widget for displaying and editing layer visualization properties."""

    _POINT_SHAPES = [
        "circle",
        "square",
        "diamond",
        "cross",
        "plus",
        "pentagram",
        "hexagram",
        "triangle",
        "triangle_up",
        "triangle_down",
        "triangle_left",
        "triangle_right",
        "pentagon",
        "hexagon",
        "star5",
        "star6",
    ]

    @property
    def _layer_name(self):
        return self._ee_layer.name

    @property
    def _layer_opacity(self):
        return self._ee_layer.opacity

    def __init__(self, host_map, layer_dict):
        """Initializes a layer manager widget.

        Args:
            host_map (geemap.Map): The geemap.Map object.
        """

        self._host_map = host_map
        if not host_map:
            raise ValueError("Must pass a valid map when creating a layer manager.")

        self._layer_dict = layer_dict

        self._ee_object = layer_dict["ee_object"]
        if isinstance(self._ee_object, (ee.Feature, ee.Geometry)):
            self._ee_object = ee.FeatureCollection(self._ee_object)

        self._ee_layer = layer_dict["ee_layer"]

        self._new_layer_name = ipywidgets.Text(
            value=f"{self._layer_name} style",
            description="New layer name:",
            style={"description_width": "initial"},
        )

        self._color_picker = ipywidgets.ColorPicker(
            concise=False,
            value="#000000",
            description="Color:",
            layout=ipywidgets.Layout(width="140px"),
            style={"description_width": "initial"},
        )

        self._color_opacity_slider = ipywidgets.FloatSlider(
            value=self._layer_opacity,
            min=0,
            max=1,
            step=0.01,
            description="Opacity:",
            continuous_update=True,
            readout=False,
            layout=ipywidgets.Layout(width="130px"),
            style={"description_width": "50px"},
        )
        self._color_opacity_slider.observe(self._color_opacity_change, names="value")

        self._color_opacity_label = ipywidgets.Label(
            style={"description_width": "initial"},
            layout=ipywidgets.Layout(padding="0px"),
        )

        self._point_size_label = ipywidgets.IntText(
            value=3,
            description="Point size:",
            layout=ipywidgets.Layout(width="110px"),
            style={"description_width": "initial"},
        )

        self._point_shape_dropdown = ipywidgets.Dropdown(
            options=self._POINT_SHAPES,
            value="circle",
            description="Point shape:",
            layout=ipywidgets.Layout(width="185px"),
            style={"description_width": "initial"},
        )

        self._line_width_label = ipywidgets.IntText(
            value=2,
            description="Line width:",
            layout=ipywidgets.Layout(width="110px"),
            style={"description_width": "initial"},
        )

        self._line_type_label = ipywidgets.Dropdown(
            options=["solid", "dotted", "dashed"],
            value="solid",
            description="Line type:",
            layout=ipywidgets.Layout(width="185px"),
            style={"description_width": "initial"},
        )

        self._fill_color_picker = ipywidgets.ColorPicker(
            concise=False,
            value="#000000",
            description="Fill Color:",
            layout=ipywidgets.Layout(width="160px"),
            style={"description_width": "initial"},
        )

        self._fill_color_opacity_slider = ipywidgets.FloatSlider(
            value=0.66,
            min=0,
            max=1,
            step=0.01,
            description="Opacity:",
            continuous_update=True,
            readout=False,
            layout=ipywidgets.Layout(width="110px"),
            style={"description_width": "50px"},
        )
        self._fill_color_opacity_slider.observe(
            self._fill_color_opacity_change, names="value"
        )

        self._fill_color_opacity_label = ipywidgets.Label(
            style={"description_width": "initial"},
            layout=ipywidgets.Layout(padding="0px"),
        )

        self._color_picker = ipywidgets.ColorPicker(
            concise=False,
            value="#000000",
            layout=ipywidgets.Layout(width="116px"),
            style={"description_width": "initial"},
        )

        self._add_color = ipywidgets.Button(
            icon="plus",
            tooltip="Add a hex color string to the palette",
            layout=ipywidgets.Layout(width="32px"),
        )
        self._del_color = ipywidgets.Button(
            icon="minus",
            tooltip="Remove a hex color string from the palette",
            layout=ipywidgets.Layout(width="32px"),
        )
        self._reset_color = ipywidgets.Button(
            icon="eraser",
            tooltip="Remove all color strings from the palette",
            layout=ipywidgets.Layout(width="34px"),
        )
        self._add_color.on_click(self._add_color_clicked)
        self._del_color.on_click(self._del_color_clicked)
        self._reset_color.on_click(self._reset_color_clicked)

        self._palette_label = ipywidgets.Text(
            value="",
            placeholder="List of hex code (RRGGBB) separated by comma",
            description="Palette:",
            tooltip="Enter a list of hex code (RRGGBB) separated by comma",
            layout=ipywidgets.Layout(width="300px"),
            style={"description_width": "initial"},
        )

        self._legend_title_label = ipywidgets.Text(
            value="Legend",
            description="Legend title:",
            tooltip="Enter a title for the legend",
            layout=ipywidgets.Layout(width="300px"),
            style={"description_width": "initial"},
        )

        self._legend_labels_label = ipywidgets.Text(
            value="Labels",
            description="Legend labels:",
            tooltip="Enter a a list of labels for the legend",
            layout=ipywidgets.Layout(width="300px"),
            style={"description_width": "initial"},
        )

        self._field_dropdown = ipywidgets.Dropdown(
            options=[],
            value=None,
            description="Field:",
            layout=ipywidgets.Layout(width="140px"),
            style={"description_width": "initial"},
        )
        self._field_dropdown.observe(self._field_changed, "value")

        self._field_values_dropdown = ipywidgets.Dropdown(
            options=[],
            value=None,
            description="Values:",
            layout=ipywidgets.Layout(width="156px"),
            style={"description_width": "initial"},
        )

        self._classes_dropdown = ipywidgets.Dropdown(
            options=["Any"] + [str(i) for i in range(3, 13)],
            description="Classes:",
            layout=ipywidgets.Layout(width="115px"),
            style={"description_width": "initial"},
        )
        self._colormap_dropdown = ipywidgets.Dropdown(
            options=["viridis"],
            value="viridis",
            description="Colormap:",
            layout=ipywidgets.Layout(width="181px"),
            style={"description_width": "initial"},
        )
        self._classes_dropdown.observe(self._classes_changed, "value")
        self._colormap_dropdown.observe(self._colormap_changed, "value")

        self._style_chk = ipywidgets.Checkbox(
            value=False,
            description="Style by attribute",
            indent=False,
            layout=ipywidgets.Layout(width="140px"),
        )
        self._legend_checkbox = ipywidgets.Checkbox(
            value=False,
            description="Legend",
            indent=False,
            layout=ipywidgets.Layout(width="70px"),
        )
        self._style_chk.observe(self._style_chk_changed, "value")
        self._legend_checkbox.observe(self._legend_chk_changed, "value")

        self._compute_label = ipywidgets.Label(value="")

        self._style_vbox = ipywidgets.VBox(
            [ipywidgets.HBox([self._style_chk, self._compute_label])]
        )

        self._colorbar_output = ipywidgets.Output(
            layout=ipywidgets.Layout(height="60px", width="300px")
        )

        is_point = common.geometry_type(self._ee_object) in ["Point", "MultiPoint"]
        self._point_size_label.disabled = not is_point
        self._point_shape_dropdown.disabled = not is_point

        super().__init__(
            layout=ipywidgets.Layout(
                padding="5px 5px 5px 8px",
                # width="330px",
                max_height="250px",
                overflow="auto",
                display="block",
            ),
            children=[
                self._new_layer_name,
                ipywidgets.HBox(
                    [
                        self._color_picker,
                        self._color_opacity_slider,
                        self._color_opacity_label,
                    ]
                ),
                ipywidgets.HBox([self._point_size_label, self._point_shape_dropdown]),
                ipywidgets.HBox([self._line_width_label, self._line_type_label]),
                ipywidgets.HBox(
                    [
                        self._fill_color_picker,
                        self._fill_color_opacity_slider,
                        self._fill_color_opacity_label,
                    ]
                ),
                self._style_vbox,
            ],
        )

    def _get_vis_params(self):
        vis = {}
        vis["color"] = self._color_picker.value[1:] + str(
            hex(int(self._color_opacity_slider.value * 255))
        )[2:].zfill(2)
        if common.geometry_type(self._ee_object) in ["Point", "MultiPoint"]:
            vis["pointSize"] = self._point_size_label.value
            vis["pointShape"] = self._point_shape_dropdown.value
        vis["width"] = self._line_width_label.value
        vis["lineType"] = self._line_type_label.value
        vis["fillColor"] = self._fill_color_picker.value[1:] + str(
            hex(int(self._fill_color_opacity_slider.value * 255))
        )[2:].zfill(2)

        return vis

    def on_apply_click(self):
        self._compute_label.value = "Computing ..."

        if self._new_layer_name.value in self._host_map.ee_layers:
            old_layer = self._new_layer_name.value
            self._host_map.remove(old_layer)

        if not self._style_chk.value:
            vis = self._get_vis_params()
            self._host_map.add_layer(
                self._ee_object.style(**vis), {}, self._new_layer_name.value
            )
            self._ee_layer.visible = False
            self._compute_label.value = ""

        elif (
            self._style_chk.value
            and len(self._palette_label.value) > 0
            and "," in self._palette_label.value
        ):
            try:
                colors = ee.List(
                    [
                        color.strip()
                        + str(hex(int(self._fill_color_opacity_slider.value * 255)))[
                            2:
                        ].zfill(2)
                        for color in self._palette_label.value.split(",")
                    ]
                )
                arr = (
                    self._ee_object.aggregate_array(self._field_dropdown.value)
                    .distinct()
                    .sort()
                )
                fc = self._ee_object.map(
                    lambda f: f.set(
                        {"styleIndex": arr.indexOf(f.get(self._field_dropdown.value))}
                    )
                )
                step = arr.size().divide(colors.size()).ceil()
                fc = fc.map(
                    lambda f: f.set(
                        {
                            "style": {
                                "color": self._color_picker.value[1:]
                                + str(hex(int(self._color_opacity_slider.value * 255)))[
                                    2:
                                ].zfill(2),
                                "pointSize": self._point_size_label.value,
                                "pointShape": self._point_shape_dropdown.value,
                                "width": self._line_width_label.value,
                                "lineType": self._line_type_label.value,
                                "fillColor": colors.get(
                                    ee.Number(
                                        ee.Number(f.get("styleIndex")).divide(step)
                                    ).floor()
                                ),
                            }
                        }
                    )
                )

                self._host_map.add_layer(
                    fc.style(**{"styleProperty": "style"}),
                    {},
                    f"{self._new_layer_name.value}",
                )

                if (
                    len(self._palette_label.value)
                    and self._legend_checkbox.value
                    and len(self._legend_labels_label.value) > 0
                    and hasattr(self._host_map, "add_legend")
                ):
                    legend_colors = [
                        color.strip() for color in self._palette_label.value.split(",")
                    ]
                    legend_keys = [
                        label.strip()
                        for label in self._legend_labels_label.value.split(",")
                    ]

                    if hasattr(self._host_map, "add_legend"):
                        self._host_map.add_legend(
                            title=self._legend_title_label.value,
                            legend_keys=legend_keys,
                            legend_colors=legend_colors,
                            layer_name=self._new_layer_name.value,
                        )
            except Exception as exc:
                self._compute_label.value = "Error: " + str(exc)

            self._ee_layer.visible = False
            self._compute_label.value = ""

    def _render_colorbar(self, colors):
        import matplotlib  # pylint: disable=import-outside-toplevel
        from matplotlib import pyplot  # pylint: disable=import-outside-toplevel

        colors = common.to_hex_colors(colors)

        _, ax = pyplot.subplots(figsize=(4, 0.3))
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
            "custom", colors, N=256
        )
        norm = matplotlib.colors.Normalize(vmin=0, vmax=1)
        matplotlib.colorbar.ColorbarBase(
            ax, norm=norm, cmap=cmap, orientation="horizontal"
        )

        self._palette_label.value = ", ".join(colors)
        self._colorbar_output.clear_output()
        with self._colorbar_output:
            pyplot.show()

    def _classes_changed(self, change):
        import matplotlib  # pylint: disable=import-outside-toplevel
        from matplotlib import pyplot  # pylint: disable=import-outside-toplevel

        if change["new"]:
            selected = change["owner"].value
            if self._colormap_dropdown.value is not None:
                n_class = None
                if selected != "Any":
                    n_class = int(self._classes_dropdown.value)

                colors = pyplot.cm.get_cmap(self._colormap_dropdown.value, n_class)
                cmap_colors = [
                    matplotlib.colors.rgb2hex(colors(i))[1:] for i in range(colors.N)
                ]
                self._render_colorbar(cmap_colors)

                if (
                    len(self._palette_label.value) > 0
                    and "," in self._palette_label.value
                ):
                    labels = [
                        f"Class {i+1}"
                        for i in range(len(self._palette_label.value.split(",")))
                    ]
                    self._legend_labels_label.value = ", ".join(labels)

    def _colormap_changed(self, change):
        import matplotlib  # pylint: disable=import-outside-toplevel
        from matplotlib import pyplot  # pylint: disable=import-outside-toplevel

        if change["new"]:
            n_class = None
            if self._classes_dropdown.value != "Any":
                n_class = int(self._classes_dropdown.value)

            colors = pyplot.cm.get_cmap(self._colormap_dropdown.value, n_class)
            cmap_colors = [
                matplotlib.colors.rgb2hex(colors(i))[1:] for i in range(colors.N)
            ]
            self._render_colorbar(cmap_colors)

            if len(self._palette_label.value) > 0 and "," in self._palette_label.value:
                labels = [
                    f"Class {i+1}"
                    for i in range(len(self._palette_label.value.split(",")))
                ]
                self._legend_labels_label.value = ", ".join(labels)

    def _fill_color_opacity_change(self, change):
        self._fill_color_opacity_label.value = str(change["new"])

    def _color_opacity_change(self, change):
        self._color_opacity_label.value = str(change["new"])

    def _add_color_clicked(self, _):
        if self._color_picker.value is not None:
            if len(self._palette_label.value) == 0:
                self._palette_label.value = self._color_picker.value[1:]
            else:
                self._palette_label.value += ", " + self._color_picker.value[1:]

    def _del_color_clicked(self, _):
        if "," in self._palette_label.value:
            items = [item.strip() for item in self._palette_label.value.split(",")]
            self._palette_label.value = ", ".join(items[:-1])
        else:
            self._palette_label.value = ""

    def _reset_color_clicked(self, _):
        self._palette_label.value = ""

    def _style_chk_changed(self, change):
        from matplotlib import pyplot  # pylint: disable=import-outside-toplevel

        if change["new"]:
            self._colorbar_output.clear_output()

            self._fill_color_picker.disabled = True
            colormap_options = pyplot.colormaps()
            colormap_options.sort()
            self._colormap_dropdown.options = colormap_options
            self._colormap_dropdown.value = "viridis"
            self._style_vbox.children = [
                ipywidgets.HBox([self._style_chk, self._compute_label]),
                ipywidgets.HBox([self._field_dropdown, self._field_values_dropdown]),
                ipywidgets.HBox([self._classes_dropdown, self._colormap_dropdown]),
                self._palette_label,
                self._colorbar_output,
                ipywidgets.HBox(
                    [
                        self._legend_checkbox,
                        self._color_picker,
                        self._add_color,
                        self._del_color,
                        self._reset_color,
                    ]
                ),
            ]
            self._compute_label.value = "Computing ..."

            self._field_dropdown.options = (
                ee.Feature(self._ee_object.first()).propertyNames().getInfo()
            )
            self._compute_label.value = ""
            self._classes_dropdown.value = "Any"
            self._legend_checkbox.value = False

        else:
            self._fill_color_picker.disabled = False
            self._style_vbox.children = [
                ipywidgets.HBox([self._style_chk, self._compute_label])
            ]
            self._compute_label.value = ""
            self._colorbar_output.clear_output()

    def _legend_chk_changed(self, change):
        if change["new"]:
            self._style_vbox.children = list(self._style_vbox.children) + [
                ipywidgets.VBox([self._legend_title_label, self._legend_labels_label])
            ]

            if len(self._palette_label.value) > 0 and "," in self._palette_label.value:
                labels = [
                    f"Class {i+1}"
                    for i in range(len(self._palette_label.value.split(",")))
                ]
                self._legend_labels_label.value = ", ".join(labels)

        else:
            self._style_vbox.children = [
                ipywidgets.HBox([self._style_chk, self._compute_label]),
                ipywidgets.HBox([self._field_dropdown, self._field_values_dropdown]),
                ipywidgets.HBox([self._classes_dropdown, self._colormap_dropdown]),
                self._palette_label,
                ipywidgets.HBox(
                    [
                        self._legend_checkbox,
                        self._color_picker,
                        self._add_color,
                        self._del_color,
                        self._reset_color,
                    ]
                ),
            ]

    def _field_changed(self, change):
        if change["new"]:
            self._compute_label.value = "Computing ..."
            options = self._ee_object.aggregate_array(
                self._field_dropdown.value
            ).getInfo()
            if options is not None:
                options = list(set(options))
                options.sort()

            self._field_values_dropdown.options = options
            self._compute_label.value = ""

    def on_import_click(self):
        vis = self._get_vis_params()
        common.create_code_cell(f"style = {str(vis)}")
        print(f"style = {str(vis)}")
