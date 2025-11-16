from typing import TYPE_CHECKING
from rich.text import TextType
from textual.widgets import DataTable
from textual import events, on

if TYPE_CHECKING:  # pragma: no cover
    from ....ui.tui import Dooit, DooitAPI


class BaseTree(DataTable[TextType], can_focus=True, inherit_bindings=False):
    @property
    def api(self) -> "DooitAPI":
        return self.tui.api

    @property
    def tui(self) -> "Dooit":
        from ....ui.tui import Dooit

        assert isinstance(self.app, Dooit)
        return self.app

    @on(events.Click)
    def on_click(self, event: events.Click) -> None:
        event.prevent_default()
