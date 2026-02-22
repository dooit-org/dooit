from typing import TYPE_CHECKING, Any, Callable, Optional

from rich.text import Text

from dooit.api.workspace import ModelType

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


class FormatterStore:
    def __init__(self, api: "DooitAPI") -> None:
        self.func: Callable
        self.api = api

    def set(self, func: Callable) -> None:
        self.func = func

    def format_value(self, model: ModelType) -> Text:
        res = self.func(model)
        if isinstance(res, str):
            return Text.from_markup(res)

        return res
