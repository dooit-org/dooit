from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union
from uuid import uuid4
from dataclasses import dataclass

from rich.text import Text
from dooit.api.workspace import ModelType
from dooit.ui.api.api_components.formatters._decorators import MUTLIPLE_FORMATTER_ATTR

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI

FormatterReturnType = Union[str, Tuple[str, bool]]


@dataclass
class FormatterFunc:
    """
    Data container holding a named formatter function and its enabled/disabled state.
    """

    name: str
    func: Callable
    disabled: bool = False


def trigger_refresh(func: Callable) -> Callable:
    """Decorator that triggers a UI refresh after the wrapped method executes."""
    def wrapper(self: "FormatterStore", *args, **kwargs):
        res = func(self, *args, **kwargs)
        self.trigger()
        return res

    return wrapper


class FormatterStore:
    """
    Manages a collection of formatter functions for a single model field.

    Formatters are applied in reverse registration order when rendering values.
    Supports adding, removing, enabling, and disabling individual formatters by ID.
    """

    def __init__(self, trigger: Callable, api: "DooitAPI") -> None:
        self.formatters = dict()
        self.trigger = trigger
        self.api = api

    @trigger_refresh
    def add(self, func: Callable, id: Optional[str] = None) -> str:
        """Register a formatter function and return its unique ID."""
        id = id or uuid4().hex
        self.formatters[id] = FormatterFunc(
            id,
            func,
        )
        return id

    def get_formatter_by_id(self, id: str) -> Optional[FormatterFunc]:
        """Return the FormatterFunc with the given ID, or None if not found."""
        return self.formatters.get(id)

    @trigger_refresh
    def remove(self, id: str) -> None:
        """Remove the formatter with the given ID, if it exists."""
        self.formatters.pop(id, None)

    @trigger_refresh
    def disable(self, id: str) -> bool:
        """Disable the formatter with the given ID. Return True if found, False otherwise."""
        formatter = self.formatters.get(id)
        if not formatter:
            return False

        formatter.disabled = True
        return True

    @trigger_refresh
    def enable(self, id: str) -> bool:
        """Enable the formatter with the given ID. Return True if found, False otherwise."""
        formatter = self.formatters.get(id)
        if not formatter:
            return False

        formatter.disabled = False
        return True

    @property
    def type1_formatter_functions(self) -> List[Callable]:
        """Return enabled single-value (non-extra) formatter functions."""
        return [
            formatter.func
            for formatter in self.formatters.values()
            if not hasattr(formatter.func, MUTLIPLE_FORMATTER_ATTR)
            and not formatter.disabled
        ]

    @property
    def type2_formatter_functions(self) -> List[Callable]:
        """Return enabled extra (multi-pass) formatter functions."""
        return [
            formatter.func
            for formatter in self.formatters.values()
            if hasattr(formatter.func, MUTLIPLE_FORMATTER_ATTR)
            and not formatter.disabled
        ]

    def _get_function_params(self, func: Callable) -> List[str]:
        return list(func.__code__.co_varnames)

    def format_value(self, value: Any, model: ModelType) -> Text:
        """Apply all enabled formatters to the given value and return the resulting Rich Text."""
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
