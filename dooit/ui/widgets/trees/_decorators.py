from functools import partial
from typing import Any, Callable, TYPE_CHECKING
from textual.widgets.option_list import OptionDoesNotExist

from dooit.api.exceptions import NoNodeError
from dooit.ui.api.events import BarNotification, ShowConfirm

if TYPE_CHECKING:  # pragma: no cover
    from .model_tree import ModelTree


def fix_highlight(func: Callable) -> Callable:
    def wrapper(self: "ModelTree", *args, **kwargs) -> Any:
        highlighted_id = self.node.id if self.highlighted is not None else None
        highlighted_index = self.highlighted

        func(self, *args, **kwargs)

        try:
            if highlighted_id is None:
                self.highlighted = highlighted_index
                self._ensure_enabled_highlight()
            else:
                self.highlight_id(highlighted_id)

        except OptionDoesNotExist:
            # The row the cursor was on is gone, so its index is all there is
            # to go back to — and what stands there now can be a rule or a
            # heading, which is nothing to put a cursor on
            self.highlighted = highlighted_index
            self._ensure_enabled_highlight()

    return wrapper


def refresh_tree(func: Callable) -> Callable:
    def wrapper(self: "ModelTree", *args, **kwargs) -> Any:
        res = func(self, *args, **kwargs)
        self.force_refresh()
        return res

    return wrapper


def require_highlighted_node(func: Callable) -> Callable:
    def wrapper(self: "ModelTree", *args, **kwargs) -> Any:
        if self.highlighted is None:
            raise NoNodeError()

        return func(self, *args, **kwargs)

    return wrapper


def reject_fixed_node(message: str) -> Callable:
    """
    Turns an edit away when the cursor is on a fixed project

    A fixed project belongs to the app rather than to the database: it can be
    walked into and read, but there is nothing there to rename, move or drop.
    The message is told which project it is talking about.
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(self: "ModelTree", *args, **kwargs) -> Any:
            if self.is_fixed_node:
                self.post_message(
                    BarNotification(
                        message.format(self.current_model.description), "warning"
                    )
                )
                return

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def require_confirmation(func: Callable) -> Callable:
    def wrapper(self: "ModelTree", *args, **kwargs) -> Any:
        function = partial(func, self, *args, **kwargs)

        if not self.api.vars.show_confirm:
            return function()

        self.post_message(ShowConfirm(function))

    return wrapper
