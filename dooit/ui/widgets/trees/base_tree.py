from collections import defaultdict
from typing import TYPE_CHECKING, Union
from textual.widgets import OptionList
from textual.widgets.option_list import Option
from textual import events, on

from dooit.api import Todo, Project
from ._decorators import require_highlighted_node

ModelType = Union[Todo, Project]

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

    @property
    def first_selectable_index(self) -> int:
        """Index of the topmost option that can be highlighted (skips the header)"""

        for index, option in enumerate(self._options):
            if not option.disabled:
                return index

        return 0

    def action_cursor_up(self) -> None:
        if (
            self.highlighted is not None
            and self.highlighted <= self.first_selectable_index
        ):
            return

        return super().action_cursor_up()

    def highlight_first_node(self) -> None:
        """Highlight the topmost node if nothing is highlighted yet"""

        if self.highlighted is None and self._options:
            index = self.first_selectable_index

            if not self._options[index].disabled:
                self.highlighted = index

    @on(events.Focus)
    def highlight_on_focus(self, _: events.Focus) -> None:
        self.highlight_first_node()

    @on(events.Click)
    def on_click(self, event: events.Click) -> None:
        event.prevent_default()
