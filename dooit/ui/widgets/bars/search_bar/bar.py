from typing import Callable, Optional
from rich.console import RenderableType

from .._base import BarBase
from ...inputs._input import Input


class SearchBar(BarBase):
    def __init__(
        self, callback: Callable, confirm: Optional[Callable] = None, *args, **kwargs
    ):
        super().__init__(callback, *args, **kwargs)
        self.confirm = confirm
        self._search = Input(value="/")
        self._search.is_editing = True

    def perform_action(self, cancel: bool):
        if cancel:
            self.callback("")
        elif self.confirm is not None:
            self.confirm(self._search.value[1:])

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
