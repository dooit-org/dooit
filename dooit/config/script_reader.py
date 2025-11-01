import importlib.util
from pathlib import Path
import inspect
from typing import final, Callable
from rich.text import Text

ScriptFunction = Callable[..., Text | None]


@final
class ScriptReader:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.module = self.load_module()
        self.main_func = self.get_main_function()
        self.main_vars = inspect.signature(self.main_func).parameters

    def load_module(self):
        spec = importlib.util.spec_from_file_location("module", self.filepath)
        module = importlib.util.module_from_spec(spec)

        assert spec is not None
        assert spec.loader is not None

        spec.loader.exec_module(module)
        return module

    def get_main_function(self) -> ScriptFunction:
        if main := getattr(self.module, "main"):
            assert isinstance(main, Callable)
            return main

        raise AttributeError("No main function found")

    def call_main(self, **kwargs: str) -> Text | None:
        return self.main_func(**kwargs)
