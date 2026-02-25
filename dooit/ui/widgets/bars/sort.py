from typing import Callable

from rich.console import RenderableType
from rich.text import Text

from dooit.models import DooitModel

from ._base import BarBase


class SortBar(BarBase):
    COMPONENT_CLASSES = {
        "option-highlighted",
    }

    def __init__(self, model: DooitModel, callback: Callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.callback = callback
        self.options = ["reverse"] + self.model.comparable_fields()
        self._selected = 0

    @property
    def selected(self) -> int:
        return self._selected

    @selected.setter
    def selected(self, val: int):
        val = max(val, 0)
        val = min(val, len(self.options) - 1)
        self._selected = val

        self.refresh()

    def perform_action(self, cancel: bool):
        if cancel:
            return

        selected = self.options[self.selected]
        self.callback(selected)

    async def handle_keypress(self, key: str) -> None:
        if key == "escape":
            return self.dismiss(cancel=True)

        if key == "enter":
            return self.dismiss(cancel=False)

        if key == "left":
            self.selected -= 1
        elif key == "right":
            self.selected += 1

    def render(self) -> RenderableType:
        highlighted_style = self.get_component_rich_style("option-highlighted")

        texts = [
            Text(f" {i} ", style=highlighted_style if index == self.selected else "")
            for index, i in enumerate(self.options)
        ]

        return Text.assemble(*texts)
