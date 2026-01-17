import importlib.util
import inspect
from pathlib import Path
from typing import Callable, final

from rich.text import Text


class ScriptFunction:
    def __init__(self, function: Callable[..., Text | None]):
        self.function = function

    @property
    def vars(self) -> dict[str, inspect.Parameter]:
        signature = inspect.signature(self.function)
        return dict(signature.parameters)

    def call(self, event=None, **kwargs):
        user_params = {k: v for k, v in kwargs.items() if not k.startswith("_")}
        if event is not None and "event" in self.vars:
            return self.function(event, **user_params)
        return self.function(**user_params)


@final
class ScriptReader:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.module = self.load_module()

    def load_module(self):
        spec = importlib.util.spec_from_file_location("module", self.filepath)

        assert spec is not None
        module = importlib.util.module_from_spec(spec)

        assert spec is not None
        assert spec.loader is not None

        spec.loader.exec_module(module)
        return module

    def get_function(self, func_name: str = "main") -> ScriptFunction:
        func = getattr(self.module, func_name, None)
        if func:
            assert isinstance(func, Callable)
            return ScriptFunction(func)

        raise AttributeError(f"No function named '{func_name}' found")
