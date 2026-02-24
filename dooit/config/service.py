from pathlib import Path
from typing import TYPE_CHECKING

from platformdirs import user_config_dir

from dooit.config.config import AppConfig
from dooit.config.refresh_service import RefreshService
from dooit.config.utils import NestedDict

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.bridge.dooit_api import DooitAPI

BASE_CONFIG = Path(__file__).parent / "default" / "config.toml"
USER_CONFIG = Path(user_config_dir("dooit")) / "config.toml"


class ConfigService:
    """Service class for applying configuration from ConfigManager."""

    def __init__(self, api: "DooitAPI", config_path: Path | None = None) -> None:
        self.api: DooitAPI = api
        self.config = self._build_config(config_path)
        self.refresh_service = self._setup_refresh_service()

    def _setup_refresh_service(self) -> RefreshService:
        scripts_config = self.config.get_scripts()
        reload_targets = {"bar": self.api.bar, "dashboard": self.api.dashboard}
        return RefreshService(scripts_config, reload_targets)

    @staticmethod
    def _build_config(config_path: Path | None = None) -> AppConfig:
        """Build merged config from base defaults and user overrides."""
        config_paths = [BASE_CONFIG, config_path or USER_CONFIG]
        base_config = NestedDict()

        for path in config_paths:
            config = NestedDict.from_path(path)
            base_config.merge(config)

        config = AppConfig.from_resolved(base_config)
        return config

    def apply_config(self) -> None:
        self._apply_theme()
        self._apply_formatters()
        self._apply_layout()
        self._apply_keys()
        self._apply_bar()
        self._apply_dashboard()

    def _apply_theme(self) -> None:
        theme = self.config.get_active_theme()
        self.api.css.set_theme(theme.as_dict())

    def _apply_formatters(self) -> None:
        self.api.formatter.todos.description.set(self.config.formatter.todo.description)
        self.api.formatter.todos.due.set(self.config.formatter.todo.due)
        self.api.formatter.todos.urgency.set(self.config.formatter.todo.urgency)
        self.api.formatter.todos.effort.set(self.config.formatter.todo.effort)
        self.api.formatter.todos.status.set(self.config.formatter.todo.status)
        self.api.formatter.todos.recurrence.set(self.config.formatter.todo.recurrence)

        self.api.formatter.workspaces.description.set(
            self.config.formatter.workspace.description
        )

    def _apply_bar(self) -> None:
        bar_config = self.config.bar
        scripts = self.config.get_scripts()
        left = [scripts[name] for name in bar_config.widgets_left]
        right = [scripts[name] for name in bar_config.widgets_right]

        self.api.bar.set(left, right)
        self.api.bar.ui_refresh()

    def _apply_dashboard(self) -> None:
        dashboard_config = self.config.dashboard
        scripts = self.config.get_scripts()
        widgets = [scripts[name] for name in dashboard_config.widgets]
        self.api.dashboard.set(widgets)

    def _apply_keys(self) -> None:
        keys_config = self.config.keys.as_dict()

        for action, key_binding in keys_config.items():
            method = getattr(self.api, action)
            self.api.keys.set(key_binding, method)

    def _apply_layout(self) -> None:
        layout_config = self.config.layout

        self.api.layouts.todo_layout = layout_config.todo
        self.api.layouts.workspace_layout = layout_config.workspace
