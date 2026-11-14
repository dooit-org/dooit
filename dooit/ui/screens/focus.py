from datetime import datetime
from math import ceil
from time import monotonic
from typing import Optional
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.widgets import Digits, Label

from dooit.api import Todo
from dooit.ui.widgets.trees.model_tree import ModelTree
from .base import BaseScreen


class FocusScreen(BaseScreen):
    """
    Blank screen showing the clock and the time left in a focus session
    """

    DEFAULT_CSS = """
    FocusScreen {
        align: center middle;

        & > Vertical {
            height: auto;
        }

        Digits, Label {
            width: auto;
        }
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Stop focus session"),
        ("c", "complete_todo", "Mark the todo as done"),
    ]

    def __init__(self, seconds: int, todo: Optional[Todo] = None):
        super().__init__()
        self.end = monotonic() + seconds
        self.todo = todo
        self.finished = False

    @property
    def remaining(self) -> int:
        return max(0, ceil(self.end - monotonic()))

    @property
    def remaining_text(self) -> str:
        # whole minutes, rounded up, so the last minute shows as 1
        return str(ceil(self.remaining / 60))

    @property
    def clock_text(self) -> str:
        return datetime.now().strftime("%H:%M")

    def compose(self) -> ComposeResult:
        with Vertical():
            if self.todo is not None:
                with Center():
                    yield Label(self.todo.description, id="focus_todo")
            with Center():
                yield Digits(self.remaining_text, id="focus_remaining")
            with Center():
                yield Label(self.clock_text, id="focus_clock")
            with Center():
                hint = Label("c mark as done · esc back", id="focus_hint")
                hint.display = False
                yield hint

    def action_complete_todo(self) -> None:
        if self.todo is None or not self.todo.pending:
            return

        self.todo.toggle_complete()
        for tree in self.app.get_screen("main").query(ModelTree):
            tree.force_refresh()

        self.app.pop_screen()

    def on_mount(self):
        self.set_interval(0.25, self.tick)

    def tick(self) -> None:
        self.query_one("#focus_remaining", Digits).update(self.remaining_text)
        self.query_one("#focus_clock", Label).update(self.clock_text)

        if self.remaining == 0 and not self.finished:
            self.finished = True
            self.add_class("-finished")
            self.app.bell()

            if self.todo is not None and self.todo.pending:
                self.query_one("#focus_hint", Label).display = True
