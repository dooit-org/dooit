from functools import partial
from typing import TYPE_CHECKING, Any, Callable

from textual.widgets.option_list import OptionDoesNotExist

from dooit.models.exceptions import NoNodeError
from dooit.ui.bridge.events import ShowConfirm

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
            else:
                self.highlight_id(highlighted_id)

        except OptionDoesNotExist:
            self.highlighted = highlighted_index

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


def require_confirmation(func: Callable) -> Callable:
    def wrapper(self: "ModelTree", *args, **kwargs) -> Any:
        function = partial(func, self, *args, **kwargs)

        if not self.api.vars.show_confirm:
            return function()

        self.post_message(ShowConfirm(function))

    return wrapper
