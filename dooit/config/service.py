from pathlib import Path

from dooit.config import ConfigData, ConfigManager
from dooit.ui.api.dooit_api import DooitAPI

BASE_CONFIG = Path(__file__).parent / "default" / "config.toml"


class ConfigService:
    """
    Service class for applying configuration from ConfigManager
    """

    def __init__(self, api: DooitAPI) -> None:
        self.api: DooitAPI = api
        self.manager: ConfigManager = ConfigManager()
        self.load_config(BASE_CONFIG)

    @property
    def config(self) -> ConfigData:
        return self.manager.get_config()

    def load_config(self, path: Path):
        self.manager.load_file(path)

    def _apply_theme(self) -> None:
        theme = self.config.theme
        if theme:
            self.api.css.set_theme(theme)

    def _apply_formatters(self) -> None:
        pass

    def _apply_bar(self) -> None:
        pass

    def _apply_dashboard(self) -> None:
        pass

    def _apply_keys(self) -> None:
        pass

    def _init_scripts(self) -> None:
        pass

    def apply_config(self) -> None:
        self._apply_theme()
        self._apply_formatters()
        self._apply_bar()
        self._apply_dashboard()
        self._apply_keys()
        self._init_scripts()
