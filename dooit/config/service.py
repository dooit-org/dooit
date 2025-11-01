from pathlib import Path
from dooit.config import ConfigManager, ConfigData
from dooit.ui.api.dooit_api import DooitAPI

BASE_CONFIG = Path(__file__).parent / "default" / "config.toml"


class ConfigService:
    """
    Service class for applying configuration from ConfigManager
    """

    def __init__(self, api: DooitAPI) -> None:
        self.api: DooitAPI = api
        self.manager: ConfigManager = ConfigManager()
        self.load_file(BASE_CONFIG)

    @property
    def config_data(self) -> ConfigData:
        return self.manager.get_config()

    def _apply_theme(self) -> None:
        theme = self.config_data.theme
        if theme:
            self.api.css.set_theme(theme)

    def apply_config(self) -> None:
        self._apply_theme()

    def load_file(self, path: Path):
        self.manager.load_file(path)
