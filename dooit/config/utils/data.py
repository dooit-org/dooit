from pathlib import Path
from typing import Union, override

import tomllib

ConfigValue = Union[bool, str, "ConfigData"]


def resolve_script_full_path(parent: Path, script: str):
    path, func_name = script.split("::")
    path = Path(path)

    if not path.is_absolute():
        path = parent / path

    return f"{path.resolve()}::{func_name}"


class ConfigData(dict[str, ConfigValue]):
    """
    A dictionary subclass that allows attribute (dot) access to keys
    and can recursively merge other dictionaries or ConfigData.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__()

    @classmethod
    def from_path(cls, path: Path) -> "ConfigData":
        if not path.exists():
            return cls()

        with open(path, "rb") as f:
            data = tomllib.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, ConfigValue]) -> "ConfigData":
        """
        Create a ConfigData instance from a regular dictionary.
        """
        config_data = cls()
        for key, value in data.items():
            if isinstance(value, dict):
                config_data[key] = cls.from_dict(value)
            else:
                if key == "_script":
                    parent = Path(__file__).parent
                    value = resolve_script_full_path(parent, value)  # type: ignore
                config_data[key] = value  # type: ignore

        return config_data

    @override
    def __setattr__(self, key: str, value: ConfigValue) -> None:
        self[key] = value

    @override
    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError as e:
            raise AttributeError(f"'ConfigData' object has no attribute '{key}'") from e

    def merge(self, other: "ConfigData") -> None:
        """
        Recursively merge another ConfigData into this one.
        For nested dictionaries, merge them recursively instead of replacing.
        """

        for key, value in other.items():
            existing = self.get(key)

            if isinstance(existing, ConfigData) and isinstance(value, ConfigData):
                existing.merge(value)
            else:
                self[key] = value
