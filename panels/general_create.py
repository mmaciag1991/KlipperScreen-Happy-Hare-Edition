import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from ks_includes.screen_panel import ScreenPanel
from panels.create_panel import Panel as CreatePanel


def remove_newlines(msg: str) -> str:
    return msg.replace('\n', ' ')


class Panel(CreatePanel):
    def __init__(self, screen, title, items=None, **panel_args):
        super().__init__(screen, title, items,**panel_args)
        grid = Gtk.Grid(row_homogeneous=True, column_homogeneous=True, hexpand=True, vexpand=True)
        scroll = self._gtk.ScrolledWindow()
        self.numpad_visible = False

        scroll.add(self.labels["parent_grid"])
        grid.attach(scroll, 0, 0, 1, 1)
        self.content.add(grid)






