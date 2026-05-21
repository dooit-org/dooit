import importlib.util
import sys
from typing import TYPE_CHECKING
from pathlib import Path
from contextlib import contextmanager

if TYPE_CHECKING:  # pragma: no cover
    from .plug import PluginManager


@contextmanager
def temporary_sys_path(path: Path):
    """Context manager to temporarily add a directory to sys.path."""

    # Temporarily add the parent directory to the path
    # to allow imports from other files in the same directory

    parent_path = str(path.parent.absolute())
    if parent_path not in sys.path:
        sys.path.insert(0, parent_path)
    try:
        yield
    finally:
        if parent_path in sys.path:
            sys.path.remove(parent_path)


def register(api: "PluginManager", path: Path) -> None:
    """Dynamically load a Python module from the given path and register its objects with the plugin manager."""
    module_name = f"dynamic_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec and spec.loader:
        parent_path = str(path.parent.absolute())
        sys.path.append(parent_path)

        with temporary_sys_path(path):
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for obj in vars(module).values():
                api.register(obj)


def load_file(api: "PluginManager", path: Path) -> bool:
    """Load a plugin file and register its contents, returning True if the file exists."""
    if not path.exists():
        return False

    if path.suffix == ".py":
        register(api, path)

    return True
