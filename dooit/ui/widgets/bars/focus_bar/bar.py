from typing import Callable
from rich.console import RenderableType
from rich.text import Text

from .._base import BarBase


class FocusBar(BarBase):
    """
    Asks for the length of a focus session in minutes
    """

    COMPONENT_CLASSES = {
        "minutes",
        "hint",
    }

    BIG_STEP = 5
    DEFAULT_MINUTES = 25
    MIN_MINUTES = 1
    MAX_MINUTES = 999

    def __init__(self, callback: Callable, *args, **kwargs):
        super().__init__(callback, *args, **kwargs)
        self.minutes = self.DEFAULT_MINUTES
        self._typing = False

    def perform_action(self, cancel: bool):
        if not cancel:
            self.callback(self.minutes)

    def increase(self, step: int):
        higher = (self.minutes // step + 1) * step
        self.minutes = min(self.MAX_MINUTES, higher)

    def decrease(self, step: int):
        lower = (self.minutes - 1) // step * step
        self.minutes = max(self.MIN_MINUTES, lower)

    def type_digit(self, digit: int):
        if not self._typing:
            self.minutes = digit
            self._typing = True
            return

        minutes = self.minutes * 10 + digit
        if minutes <= self.MAX_MINUTES:
            self.minutes = minutes

    async def handle_keypress(self, key: str) -> None:
        if key == "escape":
            return self.dismiss(cancel=True)

        if key == "enter":
            if self.minutes >= self.MIN_MINUTES:
                self.dismiss(cancel=False)
            return

        if key in ("up", "down", "left", "right"):
            step = self.BIG_STEP if key in ("up", "down") else 1
            if key in ("up", "right"):
                self.increase(step)
            else:
                self.decrease(step)
            self._typing = False
        elif key == "backspace":
            self.minutes //= 10
            self._typing = True
        elif len(key) == 1 and key.isdigit():
            self.type_digit(int(key))

        self.refresh()

    def render(self) -> RenderableType:
        minutes_style = self.get_component_rich_style("minutes")
        hint_style = self.get_component_rich_style("hint")

        return Text.assemble(
            " Focus for ",
            ("◀", hint_style),
            (f" {self.minutes} ", minutes_style),
            ("▶", hint_style),
            " min",
            (
                "   ↑/↓ ±5 · ←/→ ±1 · type minutes · enter start · esc cancel",
                hint_style,
            ),
        )
