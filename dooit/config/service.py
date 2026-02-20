from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from platformdirs import user_config_dir

from dooit.config.model import AppConfig
from dooit.config.refresh_service import RefreshService
from dooit.config.utils import ConfigData, ConfigResolver
from dooit.ui.api.dooit_api import DooitAPI
from dooit.ui.widgets.bars import StatusBarWidget

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.api_components.formatters.formatter_store import FormatterStore

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

    def __init__(self, api: DooitAPI, config_path: Path | None = None) -> None:
        self.api: DooitAPI = api
        self.config = self._build_and_validate(api, config_path)

        scripts_config = self.config.get("script", {})
        self.refresh_service = RefreshService(api, scripts_config)

    @staticmethod
    def _build_and_validate(api: DooitAPI, config_path: Path | None) -> ConfigData:
        """Build merged config and validate it before returning."""
        config = ConfigService._build_config(config_path)
        valid_actions = ConfigService._public_methods(type(api))
        valid_formatters = ConfigService._valid_formatters(api)
        AppConfig(
            config,
            valid_actions=valid_actions,
            valid_formatters=valid_formatters,
        ).validate()
        return config

    @staticmethod
    def _build_config(config_path: Path | None = None) -> ConfigData:
        """Build merged config from base defaults and user overrides."""
        config_paths = [BASE_CONFIG, config_path or USER_CONFIG]
        configs = []
        for path in config_paths:
            config = ConfigData.from_path(path)
            config = ConfigResolver.resolve(path, config)
            configs.append(config)

        base_config = ConfigData()
        for config in configs:
            base_config.merge(config)

        return base_config

    @staticmethod
    def _public_methods(cls: type) -> set[str]:
        """Return names of public callable attributes (excluding properties)."""
        return {
            name
            for name in dir(cls)
            if not name.startswith("_") and callable(getattr(cls, name, None))
        }

    @staticmethod
    def _valid_formatters(api: DooitAPI) -> dict[str, set[str]]:
        """Return mapping of model type to its valid formatter field names."""
        from dooit.ui.api.api_components.formatters import FormatterStore

        result: dict[str, set[str]] = {}
        for model_type, attr_name in _MODEL_TYPE_ATTR.items():
            formatter_group = getattr(api.formatter, attr_name)
            result[model_type] = {
                name
                for name, value in vars(formatter_group).items()
                if isinstance(value, FormatterStore)
            }
        return result

    def apply_config_pre_screen(self) -> None:
        """Apply config that doesn't require the screen to be mounted."""
        self._apply_theme()
        self._apply_formatters()
        self._apply_layout()
        self._apply_keys()

    def apply_config_post_screen(self) -> None:
        """Apply config that requires the screen to be mounted (bar, dashboard)."""
        self._apply_bar()
        self._apply_dashboard()

    def apply_config(self) -> None:
        self.apply_config_pre_screen()
        self.apply_config_post_screen()

    def _apply_theme(self) -> None:
        theme_name = self.config["general"]["theme"]
        themes = self.config["theme"]
        self.api.css.set_theme(themes[theme_name])

    def _apply_formatters(self) -> None:
        for model_type, field_name, field_config in self._iter_formatter_sections():
            entry = field_config.get("_script")
            formatter_store = self._get_formatter_store(model_type, field_name)
            formatter_store.set(entry.func)

    def _resolve_scripts(self, widget_names: list[str]) -> list[Callable]:
        """Resolve widget names to script callables."""
        return [self.refresh_service.get_script(name).func for name in widget_names]

    def _apply_bar(self) -> None:
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
        dashboard_config = self.config.get("dashboard", {})
        widget_names = list(dashboard_config.get("widgets", []))

        funcs = self._resolve_scripts(widget_names)

        self.api.dashboard.set_widget_funcs(funcs)
        self.api.dashboard.ui_refresh()
        self.refresh_service.register_target("dashboard", self.api.dashboard)

        for name in widget_names:
            self.refresh_service.add_reload_target(name, "dashboard")

    def _apply_keys(self) -> None:
        keys_config = self.config.get("keys", {})

        for action, key_binding in keys_config.items():
            method = getattr(self.api, action)
            self.api.keys.set(key_binding, method)

    def _apply_layout(self) -> None:
        layout_config = self.config.get("layout", {})

        if todo_layout := layout_config.get("todo"):
            self.api.layouts.todo_layout = todo_layout

        if workspace_layout := layout_config.get("workspace"):
            self.api.layouts.workspace_layout = workspace_layout

    def _get_formatter_store(
        self, model_type: str, field_name: str
    ) -> "FormatterStore":
        """Return formatter store for a model/field."""
        attr_name = _MODEL_TYPE_ATTR[model_type]
        formatter_group = getattr(self.api.formatter, attr_name)
        return getattr(formatter_group, field_name)

    def _iter_formatter_sections(
        self,
    ) -> Iterator[tuple[str, str, dict]]:
        """Yield (model_type, field_name, field_config) for formatter sections."""
        formatter_config = self.config.get("formatter", {})

        for model_type, fields in formatter_config.items():
            for field_name, field_config in fields.items():
                yield model_type, field_name, field_config
