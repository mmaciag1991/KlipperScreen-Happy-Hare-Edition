import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from jinja2 import Environment

from ks_includes.screen_panel import ScreenPanel
from ks_includes.KlippyGcodes import KlippyGcodes
import logging
import json

from ks_includes.widgets.autogrid import AutoGrid

class Panel(ScreenPanel):

    distances = ['.1', '.5', '1', '5', '10', '25', '50']
    distance = distances[2]  # 1mm

    def __init__(self, screen, title):
        super().__init__(screen, title)

        # menu items from config
        self.items = self._config.get_menu_items("__main laser")
        logging.info(f"Items from config: {self.items}")


        self.items_left = []
        self.items_right = []

        self.buttons = {}
        self.labels = {}
        # MUSI BYĆ zainicjalizowany od razu
        self.left_panel = None

        self.split_items()

    # =====================================================
    # ScreenPanel lifecycle
    # =====================================================

    def activate(self):
        logging.info(f"activate")
        self.build_ui()
        self.update_button_visibility()
        #self._screen.base_panel_show_all()

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):
        for child in self.content.get_children():
            self.content.remove(child)

        grid = Gtk.Grid(row_homogeneous=True, column_homogeneous=True)
        grid.set_hexpand(True)
        grid.set_vexpand(True)

        # Lewy panel
        left = self.create_left_panel()  # self.left_panel zostanie ustawione w środku
        grid.attach(left, 0, 0, 1, 1)

        # Prawy panel
        right = self.create_right_panel()
        grid.attach(right, 1, 0, 1, 1)

        self.content.add(grid)




    # =====================================================
    # Menu split
    # =====================================================

    def split_items(self):
        for config in self.items:
            for _, attr in config.items():
                orientation = "left"
                params = attr.get("params")
                if isinstance(params, str):
                    try:
                        parsed = json.loads(params)
                        orientation = parsed.get("orientation", "left")
                    except Exception as e:
                        logging.warning(f"Failed to parse params: {params} ({e})")

                if orientation == "right":
                    self.items_right.append(config)
                else:
                    self.items_left.append(config)


    # =====================================================
    # LEFT PANEL
    # =====================================================

    def create_left_panel(self):
        grid = Gtk.Grid()
        grid.get_style_context().add_class("heater-grid")

        grid.attach(self.get_top_grid(), 0, 0, 1, 1)
        grid.attach(self.get_dist_grid(), 0, 1, 1, 1)
        grid.attach(self.get_z_grid(), 0, 2, 1, 1)

        scroll = self._gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(grid)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add(scroll)

        return box

    def get_top_grid(self):
        grid = AutoGrid()

        col = 0
        row = 0

        for idx, config in enumerate(self.items_left):
            for name, attr in config.items():

                label = attr["name"].replace("{{ gettext('", "").replace("') }}", "")


                btn = self._gtk.Button(
                    attr["icon"],
                    label,
                    "max", 2, Gtk.PositionType.LEFT, 1
                )

                btn.connect("clicked", self.toggle_visibility, name)


                btn.connect(
                    "clicked",
                    self._screen._send_action,
                    attr["method"],
                    json.loads(attr["params"]) if attr.get("params") else {}
                )

                self.buttons[name] = {
                    "class": f"graph_label_laser_{idx + 1}",
                    "name": btn,
                    "visible": False
                }

                grid.attach(btn, col, row, 1, 1)

                col += 1
                if col > 1:
                    col = 0
                    row += 1

        return grid

    def get_dist_grid(self):
        grid = Gtk.Grid()

        for i, d in enumerate(self.distances):
            b = self._gtk.Button(label=d)
            b.set_direction(Gtk.TextDirection.LTR)
            b.connect("clicked", self.change_distance, d)

            ctx = b.get_style_context()
            ctx.add_class("distbutton_active" if d == self.distance else "distbutton")

            self.labels[d] = b
            grid.attach(b, i, 0, 1, 1)

        return grid

    def get_z_grid(self):
        grid = AutoGrid()

        z_plus = self._gtk.Button("z-farther", "Z+", "color3")
        z_minus = self._gtk.Button("z-closer", "Z-", "color3")

        z_plus.connect("clicked", self.move, "Z", "+")
        z_minus.connect("clicked", self.move, "Z", "-")

        grid.attach(z_plus, 0, 0, 1, 1)
        grid.attach(z_minus, 1, 0, 1, 1)

        return grid

    # =====================================================
    # RIGHT PANEL
    # =====================================================

    def create_right_panel(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )
        box.set_hexpand(True)
        box.set_vexpand(True)

        for config in self.items_right:
            for _, attr in config.items():

                label = attr["name"].replace("{{ gettext('", "").replace("') }}", "")

                btn = self._gtk.Button(
                    attr.get("icon"),
                    label,
                    attr.get("style", "color1")
                )


                # 👉 JEŚLI TO PANEL
                if attr.get("panel"):
                    btn.connect(
                        "clicked",
                        lambda _btn, panel=attr["panel"]: self._screen.show_panel(panel)
                    )

                # 👉 JEŚLI TO AKCJA
                else:
                    btn.connect(
                        "clicked",
                        self._screen._send_action,
                        attr.get("method"),
                        attr.get("params")
                    )

                enabled = True  # domyślnie włączony
                if "enable" in attr and attr["enable"]:
                    try:
                        env = Environment()
                        # renderujemy wyrażenie Jinja2
                        rendered = env.from_string(attr["enable"]).render(printer=self._screen._ws.klippy)
                        # zamieniamy wynik na bool
                        enabled = rendered.lower() in ["true", "1", "yes"]
                    except Exception as e:
                        logging.warning(f"Failed to evaluate enable for {name}: {e}")

                btn.set_sensitive(enabled)  # jeśli False, przycisk nieaktywny

                box.pack_start(btn, False, False, 0)

        return box

    # =====================================================
    # Logic
    # =====================================================

    def change_distance(self, widget, distance):
        self.labels[self.distance].get_style_context().remove_class(
            "distbutton_active"
        )
        self.labels[distance].get_style_context().add_class(
            "distbutton_active"
        )
        self.distance = distance

    def toggle_visibility(self, widget, button):
        self.buttons[button]["visible"] ^= True

        section = f"graph {self._screen.connected_printer}"
        cfg = self._config.get_config()

        if section not in cfg.sections():
            cfg.add_section(section)

        cfg.set(section, button, str(self.buttons[button]["visible"]))
        self._config.save_user_config_options()



        self.update_button_visibility()

    def update_button_visibility(self):
        for key, data in self.buttons.items():
            visible = self._config.get_config().getboolean(
                f"graph {self._screen.connected_printer}",
                key,
                fallback=False
            )
            ctx = data["name"].get_style_context()
            if visible:
                ctx.add_class(data["class"])
            else:
                ctx.remove_class(data["class"])
    def move(self, widget, axis, direction):
        if self._config.get_config()["main"].getboolean(
            f"invert_{axis.lower()}",
            False
        ):
            direction = "-" if direction == "+" else "+"

        dist = f"{direction}{self.distance}"
        speed_key = "move_speed_z" if axis == "Z" else "move_speed_xy"
        speed = self._config.get_config()["main"].getint(speed_key, 20)
        speed = 60 * max(1, speed)

        # Wysyłamy G91 (relative move), potem G1, potem G90 (absolute)
        self._screen._ws.klippy.gcode_script("G91")  # relative mode
        self._screen._ws.klippy.gcode_script(f"G1 {axis}{dist} F{speed}")
        self._screen._ws.klippy.gcode_script("G90")  # back to absolute
