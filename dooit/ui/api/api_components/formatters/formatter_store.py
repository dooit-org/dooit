from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union
from uuid import uuid4
from dataclasses import dataclass

from rich.text import Text
from dooit.api.project import ModelType
from dooit.ui.api.api_components.formatters._decorators import MUTLIPLE_FORMATTER_ATTR

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI

FormatterReturnType = Union[str, Tuple[str, bool]]


@dataclass
class FormatterFunc:
    name: str
    func: Callable
    disabled: bool = False


def trigger_refresh(func: Callable) -> Callable:
    def wrapper(self: "FormatterStore", *args, **kwargs):
        res = func(self, *args, **kwargs)
        self.trigger()
        return res

    return wrapper


class FormatterStore:
    def __init__(self, trigger: Callable, api: "DooitAPI") -> None:
        self.formatters = dict()
        self.trigger = trigger
        self.api = api

    @trigger_refresh
    def add(self, func: Callable, id: Optional[str] = None) -> str:
        id = id or uuid4().hex
        self.formatters[id] = FormatterFunc(
            id,
            func,
        )
        return id

    def get_formatter_by_id(self, id: str) -> Optional[FormatterFunc]:
        return self.formatters.get(id)

    @trigger_refresh
    def remove(self, id: str) -> None:
        self.formatters.pop(id, None)

    @trigger_refresh
    def disable(self, id: str) -> bool:
        formatter = self.formatters.get(id)
        if not formatter:
            return False

        formatter.disabled = True
        return True

    @trigger_refresh
    def enable(self, id: str) -> bool:
        formatter = self.formatters.get(id)
        if not formatter:
            return False

        formatter.disabled = False
        return True

    @property
    def type1_formatter_functions(self) -> List[Callable]:
        return [
            formatter.func
            for formatter in self.formatters.values()
            if not hasattr(formatter.func, MUTLIPLE_FORMATTER_ATTR)
            and not formatter.disabled
        ]

    @property
    def type2_formatter_functions(self) -> List[Callable]:
        return [
            formatter.func
            for formatter in self.formatters.values()
            if hasattr(formatter.func, MUTLIPLE_FORMATTER_ATTR)
            and not formatter.disabled
        ]

    def _get_function_params(self, func: Callable) -> List[str]:
        return list(func.__code__.co_varnames)

    def format_value(self, value: Any, model: ModelType) -> Text:
        params = dict(api=self.api)

        def get_extra_args(func: Callable) -> Dict[str, Any]:
            func_params = self._get_function_params(func)
            extra_args = {}

            for param in func_params:
                if param in params:
                    extra_args[param] = params[param]

            return extra_args

        res = None

        for func in reversed(self.type1_formatter_functions):
            res = func(value, model, **get_extra_args(func))

            if isinstance(res, Text):
                res = res.markup

            if res is not None:
                break

        if res is None:
            res = str(value)

        value = res
        for func in reversed(self.type2_formatter_functions):
            res = func(value, model, **get_extra_args(func))
            if res is not None:
                if isinstance(res, Text):  # pragma: no cover
                    res = res.markup

                value = str(res)

        if value:
            return Text.from_markup(value)

        return Text("-", justify="center", style="dim")
