from typing import Callable
from rich.console import RenderableType

from .._base import BarBase
from ...inputs._input import Input


class SearchBar(BarBase):
    """
    A bar widget that provides an interactive search input.

    Displays a text input prefixed with '/' and invokes the callback
    with the current filter text as the user types.
    """

    def __init__(self, callback: Callable, *args, **kwargs):
        super().__init__(callback, *args, **kwargs)
        self._search = Input(value="/")
        self._search.is_editing = True

    def perform_action(self, cancel: bool):
        """Clear the search filter by invoking the callback with an empty string if cancelled."""
        if cancel:
            self.callback("")

    async def handle_keypress(self, key: str) -> None:
        """Handle a keypress, confirming on enter, cancelling on escape, or updating the search."""
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
        """Render the search input field."""
        return self._search.draw()
