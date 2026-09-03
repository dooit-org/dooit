from typing import TYPE_CHECKING

from rich.console import RenderableType
from rich.style import Style
from rich.text import Text

from dooit.ui.api.events import ModeChanged
from .._base import BarBase

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.widgets.trees.model_tree import ModelTree

# The same rounded caps the status bar wears around its mode pill: the bar has
# been taken over mid-edit, so what stands in its place is the pill it hid
CAP_LEFT = ""
CAP_RIGHT = ""

# A field edit is an insert like any other, and says so in the same place, and
# in the same colour, the status bar would have said it
MODE_LABEL = "INSERT"


class FieldBar(BarBase):
    """
    A column being typed into, drawn where the status bar sits

    A pane that leaves a column out has nowhere to draw that column's buffer,
    and making room for one would shift every row the moment an edit started.
    The buffer goes to the bar instead, so the pane behind it never moves. The
    edit itself stays with the tree: the keys are handed straight on, and what
    is typed lands exactly where it would have.
    """

    def __init__(self, tree: "ModelTree", column: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tree = tree
        self.column = column

    def perform_action(self, cancel: bool) -> None:
        # Enter and escape reach the tree as keystrokes like any other, so the
        # edit has already been settled by the time this runs
        return

    async def handle_keypress(self, key: str) -> None:
        await self._tree.handle_keypress(key)

        if self._tree.is_editing:
            self.refresh()
            return

        self.dismiss(cancel=False)

    async def on_unmount(self):
        self.post_message(ModeChanged("NORMAL"))

        # The edit may have raised a notification on its way out, which has
        # taken the bar for itself; only what is still ours is handed back
        if self.switcher.current == self.id:
            self.switcher.current = "status_bar"

    def render(self) -> RenderableType:
        if not self._tree.is_editing:  # pragma: no cover
            return Text()

        theme = self.api.vars.theme
        cap = Style(color=theme.secondary, bgcolor=theme.background2)

        label = Text(
            f" {MODE_LABEL} ",
            style=Style(color=theme.background1, bgcolor=theme.secondary, bold=True),
        )

        buffer = self._tree.current._get_component(self.column).render_editing(theme)

        return (
            Text(CAP_LEFT, style=cap)
            + label
            + Text(CAP_RIGHT, style=cap)
            + Text(" ")
            + buffer
        )
