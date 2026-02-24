from collections import defaultdict
from typing import TYPE_CHECKING, Union

from textual import events, on
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from dooit.models import Todo, Workspace

from ._decorators import require_highlighted_node

ModelType = Union[Todo, Workspace]

if TYPE_CHECKING:  # pragma: no cover
    from ....ui.tui import Dooit, DooitAPI


class BaseTree(OptionList, can_focus=True, inherit_bindings=False):
    expanded_nodes = defaultdict(bool)

    @property
    def api(self) -> "DooitAPI":
        return self.tui.api

    @property
    def tui(self) -> "Dooit":
        from ....ui.tui import Dooit

        assert isinstance(self.app, Dooit)
        return self.app

    @property
    @require_highlighted_node
    def node(self) -> Option:
        assert self.highlighted is not None
        return self.get_option_at_index(self.highlighted)

    def action_cursor_down(self) -> None:
        if self.highlighted == len(self._options) - 1:
            return

        return super().action_cursor_down()

    def action_cursor_up(self) -> None:
        if self.highlighted == 0:
            return

        return super().action_cursor_up()

    @on(events.Click)
    def on_click(self, event: events.Click) -> None:
        event.prevent_default()
