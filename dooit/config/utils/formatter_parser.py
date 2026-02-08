from dataclasses import dataclass
from typing import Callable

from .script_reader import ScriptFunction


@dataclass
class FormatterEntry:
    func: Callable


class FormatterParser:
    @classmethod
    def parse(
        cls,
        script_func: ScriptFunction,
        field_config: dict,
        model_type: str,
    ) -> FormatterEntry:
        user_params = {k: v for k, v in field_config.items() if not k.startswith("_")}
        func = cls._build_formatter(script_func, user_params, model_type)
        return FormatterEntry(func=func)

    @classmethod
    def _build_formatter(
        cls, script_func: ScriptFunction, params: dict, model_type: str
    ) -> Callable:
        def wrapper(
            model,
            _func=script_func,
            _params=params,
            _model_type=model_type,
        ):
            return _func.call(**{_model_type: model}, **_params)

        return wrapper
