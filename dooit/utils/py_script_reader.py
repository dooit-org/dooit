import importlib.util
from pathlib import Path
from typing import Callable, final


@final
class PyScriptReader:
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
