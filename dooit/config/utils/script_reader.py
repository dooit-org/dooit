import importlib.util
from pathlib import Path
from typing import Any, Callable, final

from rich.text import Text


class ScriptFunction:
    def __init__(self, function: Callable[..., Text | None]):
        self.function = function

    def call(self, base_params: dict[str, Any], context: dict[str, Any]):
        return self.function(**base_params, context=context)


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

    def get_function(self, func_name: str = "main") -> Callable:
        func = getattr(self.module, func_name, None)
        if isinstance(func, Callable):
            return func

        raise AttributeError(f"No function named '{func_name}' found")
