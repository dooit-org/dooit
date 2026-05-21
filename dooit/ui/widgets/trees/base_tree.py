from collections import defaultdict
from typing import TYPE_CHECKING, Union
from textual.widgets import OptionList
from textual.widgets.option_list import Option
from textual import events, on

from dooit.api import Todo, Workspace
from ._decorators import require_highlighted_node

ModelType = Union[Todo, Workspace]

if TYPE_CHECKING:  # pragma: no cover
    from ....ui.tui import Dooit, DooitAPI


class BaseTree(OptionList, can_focus=True, inherit_bindings=False):
    """
    Base tree widget that extends OptionList with node expansion tracking
    and cursor movement behavior for tree-style navigation.
    """

    expanded_nodes = defaultdict(bool)

    @property
    def api(self) -> "DooitAPI":
        """Return the Dooit API instance."""
        return self.tui.api

    @property
    def tui(self) -> "Dooit":
        """Return the parent Dooit application instance."""
        from ....ui.tui import Dooit

        assert isinstance(self.app, Dooit)
        return self.app

    @property
    @require_highlighted_node
    def node(self) -> Option:
        """Return the currently highlighted option node."""
        assert self.highlighted is not None
        return self.get_option_at_index(self.highlighted)

    def action_cursor_down(self) -> None:
        """Move the cursor down, stopping at the last option."""
        if self.highlighted == len(self._options) - 1:
            return

        return super().action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move the cursor up, stopping at the first option."""
        if self.highlighted == 0:
            return

        return super().action_cursor_up()

    @on(events.Click)
    def on_click(self, event: events.Click) -> None:
        event.prevent_default()
