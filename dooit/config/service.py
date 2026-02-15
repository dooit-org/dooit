from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional

from platformdirs import user_config_dir

from dooit.config.utils import ConfigData, ConfigResolver
from dooit.config.refresh_service import RefreshService
from dooit.ui.api.dooit_api import DooitAPI

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.api_components.formatters.formatter_store import FormatterStore


BASE_CONFIG = Path(__file__).parent / "default" / "config.toml"
USER_CONFIG = Path(user_config_dir("dooit")) / "config.toml"


class ConfigService:
    """
    Service class for applying configuration from ConfigManager.
    """

    def __init__(self, api: DooitAPI, config_path: Path | None = None) -> None:
        self.api: DooitAPI = api
        self.config = self.build_config(config_path)

        scripts_config = self.config.get("script", {})
        self.refresh_service = RefreshService(api, scripts_config)

    def build_config(self, config_path: Path | None = None) -> ConfigData:
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
        theme_name = self.config["general"]["theme"]
        theme = self.config["theme"][theme_name]
        self.api.css.set_theme(theme)

    def _apply_formatters(self) -> None:
        for model_type, field_name, field_config in self._iter_formatter_sections():
            entry = field_config.get("_script")
            formatter_store = self._get_formatter_store(model_type, field_name)
            if formatter_store is None:
                continue

            formatter_store.set(entry.func)

    def _apply_bar(self) -> None:
        bar_config = self.config.get("bar", {})
        widgets_left = bar_config.get("widgets_left", [])
        widgets_right = bar_config.get("widgets_right", [])

        from dooit.ui.widgets.bars import StatusBarWidget

        bar_widgets = []
        for widget_name in list(widgets_left) + ["_spacer"] + list(widgets_right):
            if widget_name == "_spacer":
                bar_widgets.append(StatusBarWidget(lambda: "", width=0))
                continue

            script = self.refresh_service.get_script(widget_name)
            if not script:
                continue

            bar_widgets.append(StatusBarWidget(script.func))

        self.api.bar.set(bar_widgets)
        self.refresh_service.register_target("bar", self.api.bar)

    def _apply_dashboard(self) -> None:
        dashboard_config = self.config.get("dashboard", {})
        widget_names = dashboard_config.get("widgets", [])

        funcs = []
        for widget_name in widget_names:
            script = self.refresh_service.get_script(widget_name)
            if not script:
                continue
            funcs.append(script.func)

        self.api.dashboard.set_widget_funcs(funcs)
        self.api.dashboard.ui_refresh()
        self.refresh_service.register_target("dashboard", self.api.dashboard)

    def _apply_keys(self) -> None:
        keys_config = self.config.get("keys", {})

        for action, key_binding in keys_config.items():
            method = getattr(self.api, action, None)
            if method is None:
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
        formatter_group = getattr(self.api.formatter, f"{model_type}s", None)
        if formatter_group is None:
            return None
        return getattr(formatter_group, field_name, None)

    def _iter_formatter_sections(
        self,
    ) -> Iterator[tuple[str, str, dict]]:
        """Yield (model_type, field_name, field_config) for formatter sections."""
        formatter_config = self.config.get("formatter", {})

        assert isinstance(formatter_config, dict)
        for model_type, fields in formatter_config.items():
            assert isinstance(fields, dict)
            for field_name, field_config in fields.items():
                assert isinstance(field_config, dict)
                yield model_type, field_name, field_config
