from pathlib import Path

import tomllib
from platformdirs import user_config_dir
from typing_extensions import Any

BASE_CONFIG = Path(__file__).parent / "default" / "config.toml"
USER_CONFIG = Path(user_config_dir("dooit")) / "config.toml"


def resolve_script_full_path(parent: Path, script: str):
    path, func_name = script.split("::")
    path = Path(path)

    if not path.is_absolute():
        path = parent / path

    return f"{path.resolve()}::{func_name}"


class ConfigReader(dict[str, Any]):
    """
    A dictionary subclass that allows attribute (dot) access to keys
    and can recursively merge other dictionaries
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.load_defaults()

    def load_defaults(self):
        self.from_path(BASE_CONFIG)

        if USER_CONFIG.exists():
            self.merge(ConfigReader.from_path(USER_CONFIG))

    @classmethod
    def from_path(cls, path: Path) -> "ConfigReader":
        if not path.exists():
            return cls()

        with open(path, "rb") as f:
            data = tomllib.load(f)

        return cls.from_dict(data, path.parent)

    @classmethod
    def from_dict(cls, data: dict[str, Any], parent: Path) -> "ConfigReader":
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

    def merge(self, other: "ConfigReader") -> None:
        """
        Recursively merge another ConfigReader into this one.
        For nested dictionaries, merge them recursively instead of replacing.
        """

        for key, value in other.items():
            existing = self.get(key)

            if isinstance(existing, ConfigReader) and isinstance(value, ConfigReader):
                existing.merge(value)
            else:
                self[key] = value
