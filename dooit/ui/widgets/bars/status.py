from rich.console import RenderableType
from rich.table import Table

from ._base import BarBase


class StatusBar(BarBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widgets_left = []
        self.widgets_right = []

    def render(self) -> RenderableType:
        self.widgets_left = self.api.bar.widgets_left
        self.widgets_right = self.api.bar.widgets_right

        table = Table.grid(expand=True, padding=0)
        row = []

        for widget in self.widgets_left:
            table.add_column(widget.entry.name)
            row.append(widget._cached)

        table.add_column("spacer", ratio=1)
        row.append("")

        for widget in self.widgets_right:
            table.add_column(widget.entry.name)
            row.append(widget._cached)

        table.add_row(*row)
        return table
