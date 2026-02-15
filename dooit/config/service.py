import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional

from platformdirs import user_config_dir

from dooit.config.errors import ConfigError, ConfigValidationError
from dooit.config.utils import ConfigData, ConfigResolver
from dooit.config.refresh_service import RefreshService
from dooit.ui.api.dooit_api import DooitAPI
from dooit.ui.widgets.bars import StatusBarWidget

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.api_components.formatters.formatter_store import FormatterStore

logger = logging.getLogger(__name__)

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
        self.config = self.build_config(config_path)

        scripts_config = self.config.get("script", {})
        self.refresh_service = RefreshService(api, scripts_config)

    @staticmethod
    def build_config(config_path: Path | None = None) -> ConfigData:
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
        general = self.config.get("general")
        if not isinstance(general, dict):
            raise ConfigError("Missing [general] section in config")

        theme_name = general.get("theme")
        if theme_name is None:
            raise ConfigError("Missing 'theme' key in [general] section")

        themes = self.config.get("theme", {})
        if theme_name not in themes:
            available = ", ".join(themes.keys()) if themes else "(none)"
            raise ConfigError(
                f"Theme '{theme_name}' not found. Available themes: {available}"
            )

        self.api.css.set_theme(themes[theme_name])

    def _apply_formatters(self) -> None:
        for model_type, field_name, field_config in self._iter_formatter_sections():
            entry = field_config.get("_script")
            formatter_store = self._get_formatter_store(model_type, field_name)
            if formatter_store is None:
                logger.warning(
                    "Unknown formatter target '%s.%s' — skipping",
                    model_type,
                    field_name,
                )
                continue

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
            method = getattr(self.api, action, None)
            if method is None:
                logger.warning(
                    "Key binding references unknown action '%s' — skipping",
                    action,
                )
                continue

            self.api.keys.set(key_binding, method)

    def _apply_layout(self) -> None:
        layout_config = self.config.get("layout", {})

        if todo_layout := layout_config.get("todo"):
            self.api.layouts.todo_layout = todo_layout

        if workspace_layout := layout_config.get("workspace"):
            self.api.layouts.workspace_layout = workspace_layout

    def _get_formatter_store(
        self, model_type: str, field_name: str
    ) -> Optional["FormatterStore"]:
        """Return formatter store for a model/field, or None if missing."""
        attr_name = _MODEL_TYPE_ATTR.get(model_type)
        if attr_name is None:
            return None

        formatter_group = getattr(self.api.formatter, attr_name, None)
        if formatter_group is None:
            return None

        return getattr(formatter_group, field_name, None)

    def _iter_formatter_sections(
        self,
    ) -> Iterator[tuple[str, str, dict]]:
        """Yield (model_type, field_name, field_config) for formatter sections."""
        formatter_config = self.config.get("formatter", {})

        if not isinstance(formatter_config, dict):
            raise ConfigValidationError(
                f"[formatter] must be a table, got {type(formatter_config).__name__}"
            )

        for model_type, fields in formatter_config.items():
            if not isinstance(fields, dict):
                raise ConfigValidationError(
                    f"[formatter.{model_type}] must be a table, "
                    f"got {type(fields).__name__}"
                )

            for field_name, field_config in fields.items():
                if not isinstance(field_config, dict):
                    raise ConfigValidationError(
                        f"[formatter.{model_type}.{field_name}] must be a table, "
                        f"got {type(field_config).__name__}"
                    )

                yield model_type, field_name, field_config
