from typing import Callable

from rich.console import RenderableType

from ..inputs._input import Input
from ._base import BarBase


class SearchBar(BarBase):
    def __init__(self, callback: Callable, *args, **kwargs):
        super().__init__(callback, *args, **kwargs)
        self._search = Input(value="/")
        self._search.is_editing = True

    def perform_action(self, cancel: bool):
        if cancel:
            self.callback("")

    async def handle_keypress(self, key: str) -> None:
        if key == "enter":
            self.dismiss(cancel=False)

        elif key == "escape":
            self.dismiss(cancel=True)

        else:
            self._search.keypress(key)
            filter = self._search.value[1:]
            self.callback(filter)
            self.refresh()

    def render(self) -> RenderableType:
        return self._search.draw()
