from importlib.machinery import ModuleSpec
import importlib.util
from os import path
from typing import Any, Dict, Optional
import appdirs

user_config = path.join(appdirs.user_config_dir("dooit"), "config.py")
default_config = path.join(path.dirname(__file__), "default_config.py")

default_spec = importlib.util.spec_from_file_location("default_config", default_config)
if path.isfile(user_config):
    user_spec = importlib.util.spec_from_file_location("user_config", user_config)
else:
    user_spec = default_spec


def get_vars(spec: Optional[ModuleSpec]) -> Dict[str, Any]:
    if spec and spec.loader:
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)
        return vars(foo)

    return {}


class Config:
    def __init__(self) -> None:
        self.update()

    def update(self):
        self._d = get_vars(default_spec) | get_vars(user_spec)

    def get(self, var: str) -> Any:
        return self._d[var]