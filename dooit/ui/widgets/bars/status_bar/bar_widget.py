from collections.abc import Callable
from rich.text import TextType, Text
from typing import Optional


class StatusBarWidget:
    """
    A single widget component rendered within the status bar.

    Wraps a callable that produces rich text content and an optional
    fixed width for column sizing in the status bar grid.
    """

    def __init__(
        self, func: Callable[..., TextType], width: Optional[int] = None
    ) -> None:
        self.func = func
        self.width = width

    @property
    def value(self) -> str:
        """Return the current string value produced by the widget's function."""
        res = getattr(self.func, "__dooit_value", "")

        if isinstance(res, Text):
            return res.markup

        return str(res)

    def render(self) -> TextType:
        """Render the widget's value as rich markup text."""
        return Text.from_markup(self.value)
