from typing import Callable

from rich.text import Text

from dooit.models.workspace import ModelType


class FormatterStore:
    def __init__(self) -> None:
        self.func: Callable

    def set(self, func: Callable) -> None:
        self.func = func

    def format_value(self, model: ModelType) -> Text:
        res = self.func(model)
        if isinstance(res, str):
            return Text.from_markup(res)

        return res
