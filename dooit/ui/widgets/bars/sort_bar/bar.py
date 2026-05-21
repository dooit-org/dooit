from typing import Callable
from rich.console import RenderableType
from rich.text import Text
from dooit.ui.widgets.bars._base import BarBase
from dooit.api import DooitModel


class SortBar(BarBase):
    """
    A bar widget that presents sortable field options for a model.

    Displays a horizontal list of sort options that can be navigated
    with arrow keys and selected with enter.
    """

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
        """Return the index of the currently selected sort option."""
        return self._selected

    @selected.setter
    def selected(self, val: int):
        val = max(val, 0)
        val = min(val, len(self.options) - 1)
        self._selected = val

        self.refresh()

    def perform_action(self, cancel: bool):
        """Invoke the callback with the selected sort field if not cancelled."""
        if cancel:
            return

        selected = self.options[self.selected]
        self.callback(selected)

    async def handle_keypress(self, key: str) -> None:
        """Handle a keypress to navigate options or confirm/cancel the selection."""
        if key == "escape":
            return self.dismiss(cancel=True)

        if key == "enter":
            return self.dismiss(cancel=False)

        if key == "left":
            self.selected -= 1
        elif key == "right":
            self.selected += 1

    def render(self) -> RenderableType:
        """Render the sort options with the current selection highlighted."""
        highlighted_style = self.get_component_rich_style("option-highlighted")

        texts = [
            Text(f" {i} ", style=highlighted_style if index == self.selected else "")
            for index, i in enumerate(self.options)
        ]

        return Text.assemble(*texts)
