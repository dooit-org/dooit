from pathlib import Path

import tomllib
from typing_extensions import Any, Self


def resolve_script_full_path(parent: Path, script: str):
    path, func_name = script.split("::")
    path = Path(path)

    if not path.is_absolute():
        path = parent / path

    return f"{path.resolve()}::{func_name}"


class NestedDict(dict[str, Any]):
    """
    A dictionary subclass that allows attribute (dot) access to keys
    and can recursively merge other dictionaries
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__()

    @classmethod
    def from_path(cls, path: Path) -> "NestedDict":
        if not path.exists():
            return cls()

        with open(path, "rb") as f:
            data = tomllib.load(f)

        return cls.from_dict(data, path.parent)

    @classmethod
    def from_dict(cls, data: dict[str, Any], parent: Path) -> "NestedDict":
        """
        Create a ConfigData instance from a regular dictionary.
        """
        config_data = cls()
        for key, value in data.items():
            if isinstance(value, dict):
                config_data[key] = cls.from_dict(value, parent)
            else:
                if key == "_script":
                    value = resolve_script_full_path(parent, value)  # type: ignore
                config_data[key] = value  # type: ignore

        return config_data

    def merge(self, other: Self) -> None:
        """
        Recursively merge another ConfigData into this one.
        For nested dictionaries, merge them recursively instead of replacing.
        """

        for key, value in other.items():
            existing = self.get(key)

            if isinstance(existing, NestedDict) and isinstance(value, NestedDict):
                existing.merge(value)
            else:
                self[key] = value
