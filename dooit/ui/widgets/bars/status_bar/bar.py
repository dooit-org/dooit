from typing import TYPE_CHECKING

from rich.console import RenderableType
from rich.table import Table

if TYPE_CHECKING:
    from dooit.config.types import ScriptField

from .._base import BarBase


class StatusBar(BarBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widgets_left = []
        self.widgets_right = []

    def set_scripts(
        self, widgets_left: list["ScriptField"], widgets_right: list["ScriptField"]
    ) -> None:
        self.widgets_left = widgets_left
        self.widgets_right = widgets_right
        self.ui_refresh()

    def ui_refresh(self) -> None:
        self.refresh()

    def render(self) -> RenderableType:
        table = Table.grid(expand=True, padding=0)
        row = []

        for widget in self.widgets_left:
            table.add_column(widget.entry.name)
            row.append(widget._cached)
        table.add_column("spacer", ratio=1)
        for widget in self.widgets_right:
            table.add_column(widget.entry.name)
            row.append(widget._cached)

        table.add_row(*row)
        return table
