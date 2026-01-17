import tomllib
from pathlib import Path
from .data import ConfigData


class ConfigManager:
    """
    A manager that reads configuration from a TOML file and converts it to ConfigData.
    """

    def __init__(self) -> None:
        self._config_data: ConfigData = ConfigData()

    def load_file(self, config_path: Path | str) -> None:
        """
        Load and merge configuration from a TOML file into the current ConfigData.

        Args:
            config_path: Path to the TOML configuration file

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            tomllib.TOMLDecodeError: If the file contains invalid TOML
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        new_config = ConfigData.from_dict(data)
        self._config_data.merge(new_config)

    def get_config(self) -> ConfigData:
        return self._config_data
