from typing import Callable, Optional
from rich.console import RenderableType
from rich.text import Text

from dooit.api import Todo

from .._base import BarBase


class FocusBar(BarBase):
    """
    Asks for the length of a focus session in minutes
    """

    COMPONENT_CLASSES = {
        "minutes",
        "hint",
        "todo",
    }

    BIG_STEP = 5
    DEFAULT_MINUTES = 25
    MIN_MINUTES = 1
    MAX_MINUTES = 999

    MAX_TODO_WIDTH = 40

    def __init__(
        self, callback: Callable, todo: Optional[Todo] = None, *args, **kwargs
    ):
        super().__init__(callback, *args, **kwargs)
        self.todo = todo
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

        if self.todo is None:
            subject = Text(" Focus for ")
        else:
            description = self.todo.description
            if len(description) > self.MAX_TODO_WIDTH:
                description = description[: self.MAX_TODO_WIDTH - 1] + "…"

            subject = Text.assemble(
                " Focus on ",
                (description, self.get_component_rich_style("todo")),
                " for ",
            )

        return Text.assemble(
            subject,
            ("◀", hint_style),
            (f" {self.minutes} ", minutes_style),
            ("▶", hint_style),
            " min",
            (
                "   ↑/↓ ±5 · ←/→ ±1 · type minutes · enter start · esc cancel",
                hint_style,
            ),
        )
