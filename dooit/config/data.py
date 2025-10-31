from typing import override, Union
from string import Template

ConfigValue = Union[bool, str, "ConfigData"]


class ConfigData(dict[str, ConfigValue]):
    """
    A dictionary subclass that allows attribute (dot) access to keys
    and can recursively merge other dictionaries or ConfigData.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__()

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
                config_data[key] = value  # type: ignore

        return config_data

    def __getattr__(self, key: str) -> ConfigValue:
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError(f"'ConfigData' object has no attribute '{key}'") from e

    @override
    def __setattr__(self, key: str, value: ConfigValue) -> None:
        self[key] = value

    @override
    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError as e:
            raise AttributeError(f"'ConfigData' object has no attribute '{key}'") from e

    def resolve_vars(self, theme: dict[str, str]) -> None:
        """
        Recursively resolve string variables in the ConfigData using string.Template.
        """

        for key, value in self.items():
            if isinstance(value, str):
                template = Template(value)
                self[key] = template.substitute(theme)
            elif isinstance(value, dict):
                value.resolve_vars(theme)

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

        self.resolve_vars(self.theme)
