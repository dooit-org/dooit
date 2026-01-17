from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, Optional

from platformdirs import user_config_dir

from dooit.config.utils import ConfigData, ConfigResolver
from dooit.config.utils.script_reader import ScriptFunction
from dooit.config.utils.parsers import (
    parse_refresh_interval,
    parse_event,
    parse_reload_targets,
)
from dooit.ui.api.api_components.formatters._decorators import MUTLIPLE_FORMATTER_ATTR
from dooit.ui.api.dooit_api import DooitAPI
from dooit.ui.api.plug import DOOIT_EVENT_ATTR, DOOIT_TIMER_ATTR

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.api_components.formatters.formatter_store import FormatterStore


BASE_CONFIG = Path(__file__).parent / "default" / "config.toml"
USER_CONFIG = Path(user_config_dir("dooit")) / "config.toml"


@dataclass
class ScriptEntry:
    name: str
    func: Callable
    reload_targets: set[str] = field(default_factory=set)


class ConfigService:
    """
    Service class for applying configuration from ConfigManager
    """

    def __init__(self, api: DooitAPI, config_path: Path | None = None) -> None:
        self.api: DooitAPI = api
        self.config = self.build_config(config_path)

        self._dashboard_widgets: list[str] = []

    def build_config(self, config_path: Path | None = None) -> None:
        config_paths = [BASE_CONFIG, config_path or USER_CONFIG]
        configs = []
        for path in config_paths:
            config = ConfigData.from_path(path)
            config = ConfigResolver.resolve_script_funcs(path, config)
            configs.append(config)

        base_config = ConfigData()
        for config in configs:
            base_config.merge(config)

        return base_config

    def apply_config_pre_screen(self) -> None:
        """Apply config that doesn't require the screen to be mounted."""
        self._apply_theme()
        self._init_scripts()
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
            script_func = field_config.get("_script")
            if not isinstance(script_func, ScriptFunction):
                continue

            formatter_store = self._get_formatter_store(model_type, field_name)
            if formatter_store is None:
                continue

            clear_mode = bool(field_config.get("_clear", True))
            user_params = self._filter_user_params(field_config)
            formatter_id = f"config_{model_type}_{field_name}"

            if clear_mode:
                formatter_store.formatters.clear()
                wrapper = self._build_override_formatter(
                    script_func, user_params, model_type
                )
            else:
                wrapper = self._build_enhancer_formatter(
                    script_func, user_params, model_type
                )

            formatter_store.add(wrapper, id=formatter_id)

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

            script_entry = self._get_script_entry(widget_name)
            if not script_entry:
                continue

            script_entry.reload_targets.add("bar")
            bar_widgets.append(StatusBarWidget(script_entry.func))

        self.api.bar.set(bar_widgets)

    def _apply_dashboard(self) -> None:
        dashboard_config = self.config.get("dashboard", {})
        widget_names = dashboard_config.get("widgets", [])

        self._dashboard_widgets = []
        for widget_name in widget_names:
            script_entry = self._get_script_entry(widget_name)
            if not script_entry:
                continue

            script_entry.reload_targets.add("dashboard")
            self._dashboard_widgets.append(widget_name)

        self._render_dashboard()

    def _apply_keys(self) -> None:
        keys_config = self.config.get("keys", {})

        for action, key_binding in keys_config.items():
            method = getattr(self.api, action, None)
            if method is None:
                continue

            self.api.keys.set(key_binding, method)

    def _init_scripts(self) -> None:
        self._scripts = {}
        scripts_config = self.config.get("script", {})

        for name, script_config in scripts_config.items():
            script_func = script_config.get("_script")
            if not isinstance(script_func, ScriptFunction):
                continue

            user_params = self._filter_user_params(script_config)
            reload_targets = parse_reload_targets(script_config.get("_reload"))

            wrapper = self._build_script_wrapper(
                script_func,
                user_params,
                reload_targets,
            )
            entry = ScriptEntry(
                name=name,
                func=wrapper,
                reload_targets=reload_targets,
            )
            self._scripts[name] = entry

            if self._register_refresh(script_config, wrapper):
                continue

            result = script_func.call(**user_params)
            setattr(wrapper, "__dooit_value", result)

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

    def _filter_user_params(self, config: dict) -> dict:
        """Return only user params (non-underscore keys)."""
        return {k: v for k, v in config.items() if not k.startswith("_")}

    def _get_script_entry(self, name: str) -> Optional[ScriptEntry]:
        """Return cached script entry by name."""
        return self._scripts.get(name)

    def _build_override_formatter(
        self, script_func: ScriptFunction, params: dict, model_type: str
    ) -> Callable:
        """Build a formatter that clears existing formatters and returns new value."""

        def wrapper(
            _,
            model,
            _func=script_func,
            _params=params,
            _model_type=model_type,
            **kwargs,
        ):
            return _func.call(**{_model_type: model}, **_params)

        return wrapper

    def _build_enhancer_formatter(
        self, script_func: ScriptFunction, params: dict, model_type: str
    ) -> Callable:
        """Build a formatter that receives formatted text and returns enhanced text."""

        def wrapper(
            formatted_text,
            model,
            _func=script_func,
            _params=params,
            _model_type=model_type,
            **kwargs,
        ):
            return _func.call(
                formatted_text=formatted_text, **{_model_type: model}, **_params
            )

        setattr(wrapper, MUTLIPLE_FORMATTER_ATTR, True)
        return wrapper

    def _register_refresh(self, script_config: dict, func: Callable) -> bool:
        """Register refresh hooks; returns True when a refresh was registered."""
        refresh = script_config.get("_refresh")
        if refresh is None:
            return False

        if refresh.startswith("every"):
            interval = parse_refresh_interval(refresh)
            if interval is None:
                return False
            setattr(func, DOOIT_TIMER_ATTR, interval)
            self.api.plugin_manager.register(func)
            return True

        if refresh.startswith("on"):
            event_cls = parse_event(refresh)
            if event_cls is None:
                return False
            setattr(func, DOOIT_EVENT_ATTR, [event_cls])
            self.api.plugin_manager.register(func)
            return True

        return False

    def _build_script_wrapper(
        self,
        script_func: ScriptFunction,
        user_params: dict,
        reload_targets: set[str],
    ) -> Callable:
        def wrapper(api, event=None):
            result = script_func.call(event=event, **user_params)
            setattr(wrapper, "__dooit_value", result)
            self._rerender_targets(reload_targets)
            return result

        return wrapper

    def _rerender_targets(self, targets: Iterable[str]) -> None:
        """Rerender only the requested UI targets."""
        if "bar" in targets:
            try:
                self.api.app.bar.refresh()
            except Exception:
                pass

        if "dashboard" in targets:
            self._render_dashboard()

        if "todos" in targets:
            self._refresh_todos()

        if "workspaces" in targets:
            self._refresh_workspaces()

    def _render_dashboard(self) -> None:
        """Render dashboard items using cached script values."""
        items = []
        for widget_name in self._dashboard_widgets:
            script_entry = self._scripts.get(widget_name)
            if not script_entry:
                continue

            value = getattr(script_entry.func, "__dooit_value", "")
            items.append(value)

        self.api.dashboard.set(items)

    def _refresh_todos(self) -> None:
        """Force refresh all todo trees."""
        from dooit.ui.widgets.trees import TodosTree

        for widget in self.api.app.screen.query(TodosTree):
            widget.force_refresh()

    def _refresh_workspaces(self) -> None:
        """Force refresh all workspace trees."""
        from dooit.ui.widgets.trees import WorkspacesTree

        for widget in self.api.app.screen.query(WorkspacesTree):
            widget.force_refresh()

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
