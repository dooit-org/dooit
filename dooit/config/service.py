from pathlib import Path
from typing import TYPE_CHECKING

from platformdirs import user_config_dir

from dooit.config.config import AppConfig
from dooit.config.refresh_service import RefreshService
from dooit.config.utils import NestedDict
from dooit.ui.widgets.bars import StatusBarWidget

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI

BASE_CONFIG = Path(__file__).parent / "default" / "config.toml"
USER_CONFIG = Path(user_config_dir("dooit")) / "config.toml"


def _noop_func() -> str:
    return ""


_MODEL_TYPE_ATTR: dict[str, str] = {
    "todo": "todos",
    "workspace": "workspaces",
}


class ConfigService:
    """Service class for applying configuration from ConfigManager."""

    def __init__(self, api: "DooitAPI", config_path: Path | None = None) -> None:
        self.api: DooitAPI = api
        self.config = self._build_config(config_path)

        scripts_config = self.config.get_scripts()
        self.refresh_service = RefreshService(api, scripts_config)

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

    # def _resolve_scripts(self, widget_names: list[str]) -> list[Callable]:
    #     """Resolve widget names to script callables."""
    #     return [self.refresh_service.get_script(name).func for name in widget_names]

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
        return
        bar_config = self.config.get("bar", {})
        widgets_left = list(bar_config.get("widgets_left", []))
        widgets_right = list(bar_config.get("widgets_right", []))

        left_funcs = self._resolve_scripts(widgets_left)
        right_funcs = self._resolve_scripts(widgets_right)

        bar_widgets = (
            [StatusBarWidget(f) for f in left_funcs]
            + [StatusBarWidget(_noop_func, width=0)]
            + [StatusBarWidget(f) for f in right_funcs]
        )

        self.api.bar.set(bar_widgets)
        self.refresh_service.register_target("bar", self.api.bar)

        for name in widgets_left + widgets_right:
            self.refresh_service.add_reload_target(name, "bar")

    def _apply_dashboard(self) -> None:
        return
        dashboard_config = self.config.get("dashboard", {})
        widget_names = list(dashboard_config.get("widgets", []))

        funcs = self._resolve_scripts(widget_names)

        self.api.dashboard.set_widget_funcs(funcs)
        self.api.dashboard.ui_refresh()
        self.refresh_service.register_target("dashboard", self.api.dashboard)

        for name in widget_names:
            self.refresh_service.add_reload_target(name, "dashboard")

    def _apply_keys(self) -> None:
        keys_config = self.config.keys.as_dict()

        for action, key_binding in keys_config.items():
            method = getattr(self.api, action)
            self.api.keys.set(key_binding, method)

    def _apply_layout(self) -> None:
        layout_config = self.config.layout

        self.api.layouts.todo_layout = layout_config.todo
        self.api.layouts.workspace_layout = layout_config.workspace
