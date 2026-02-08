from typing import TYPE_CHECKING, Any, Callable, Optional

from rich.text import Text
from dooit.api.workspace import ModelType

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


class FormatterStore:
    def __init__(self, api: "DooitAPI") -> None:
        self.api = api
        self.func: Optional[Callable] = None

    def set(self, func: Callable) -> None:
        self.func = func

    def format_value(self, value: Any, model: ModelType) -> Text:
        res = None

        if self.func:
            res = self.func(model)

            if isinstance(res, Text):
                res = res.markup

        if res is None:
            res = str(value)

        if res:
            return Text.from_markup(res)

        return Text("-", justify="center", style="dim")
