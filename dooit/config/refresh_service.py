from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Iterable, Protocol, runtime_checkable

from dooit.config.errors import ConfigError
from dooit.config.utils.script_parser import ScriptEntry, RefreshConfig, RefreshKind
from dooit.ui.api.plug import DOOIT_EVENT_ATTR, DOOIT_TIMER_ATTR

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


@runtime_checkable
class Refreshable(Protocol):
    def ui_refresh(self) -> None: ...


@dataclass
class _CachedScript:
    name: str
    func: Callable
    reload_targets: set[str] = field(default_factory=set)


class RefreshService:
    """
    Manages script wrappers, __dooit_value caching, timer/event registration,
    and dispatches ui_refresh() to registered targets.
    """

    def __init__(self, api: "DooitAPI", scripts_config: dict) -> None:
        self.api = api
        self._scripts: dict[str, _CachedScript] = {}
        self._targets: dict[str, Refreshable] = {}

        for name, script_config in scripts_config.items():
            entry: ScriptEntry | None = script_config.get("_script")
            if entry is None:
                raise ConfigError(
                    f"[script.{name}] is missing a '_script' key. "
                    f"Every script section must reference a Python function "
                    f"via '_script = \"./path::function\"'."
                )
            self._register_script(name, entry)

    # --- Target registry ---

    def register_target(self, name: str, target: Refreshable) -> None:
        """Register a UI component as a refresh target."""
        self._targets[name] = target

    def _refresh_targets(self, target_names: Iterable[str]) -> None:
        """Call ui_refresh() on each registered target by name."""
        for name in target_names:
            if target := self._targets.get(name):
                target.ui_refresh()

    # --- Script lifecycle (internal) ---

    def get_script(self, name: str) -> _CachedScript:
        """Return a cached script by name.

        Raises:
            ConfigError: If the script name is not registered.
        """
        script = self._scripts.get(name)
        if script is None:
            available = ", ".join(sorted(self._scripts)) or "(none)"
            raise ConfigError(
                f"Script '{name}' not found. "
                f"Make sure it is defined under [script.{name}] in your config. "
                f"Available scripts: {available}"
            )
        return script

    def has_script(self, name: str) -> bool:
        """Check whether a script with the given name is registered."""
        return name in self._scripts

    def add_reload_target(self, script_name: str, target_name: str) -> None:
        """Mark a script so it refreshes the given target when it updates."""
        self._scripts[script_name].reload_targets.add(target_name)

    def _register_script(self, name: str, entry: ScriptEntry) -> None:
        """Build wrapper, cache result, register refresh if needed."""
        wrapper = self._build_script_wrapper(entry)
        self._scripts[name] = _CachedScript(
            name=name,
            func=wrapper,
            reload_targets=entry.reload_targets,
        )

        if entry.refresh:
            self._register_refresh(entry.refresh, wrapper)
        else:
            result = entry.func.call(**entry.user_params)
            setattr(wrapper, "__dooit_value", result)

    def _build_script_wrapper(self, entry: ScriptEntry) -> Callable:
        def wrapper(api, event=None):
            result = entry.func.call(event=event, **entry.user_params)
            setattr(wrapper, "__dooit_value", result)
            self._refresh_targets(entry.reload_targets)
            return result

        return wrapper

    def _register_refresh(self, refresh: RefreshConfig, func: Callable) -> None:
        """Register a timer or event refresh hook for a script wrapper."""
        if refresh.kind is RefreshKind.INTERVAL:
            setattr(func, DOOIT_TIMER_ATTR, refresh.value)
            self.api.plugin_manager.register(func)
        elif refresh.kind is RefreshKind.EVENT:
            setattr(func, DOOIT_EVENT_ATTR, [refresh.value])
            self.api.plugin_manager.register(func)
