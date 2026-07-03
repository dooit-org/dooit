from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Literal, Optional

from dooit.config.errors import ConfigError, ConfigValidationError
from dooit.utils.py_script_reader import PyScriptReader

if TYPE_CHECKING:
    from dooit.ui.bridge.events import DooitEvent


class ScriptKeyword(str, Enum):
    SCRIPT = "_script"
    REFRESH = "_refresh"
    RELOAD = "_reload"


class RefreshKind(str, Enum):
    INTERVAL = "interval"
    EVENT = "event"


@dataclass(frozen=True)
class RefreshConfig:
    kind: RefreshKind
    value: int | type[DooitEvent]


ReloadTarget = Literal["bar", "dashboard", "todo", "workspace"]


@dataclass
class ScriptEntry:
    name: str
    func: Callable
    refresh: RefreshConfig
    reload_targets: set[ReloadTarget] = field(default_factory=set)
    context: dict = field(default_factory=dict)


class ScriptReaderFactory:
    _cache = {}

    @classmethod
    def get_reader(cls, path: Path) -> PyScriptReader:
        resolved_path = path.resolve()
        if resolved_path not in cls._cache:
            cls._cache[resolved_path] = PyScriptReader(resolved_path)
        return cls._cache[resolved_path]


class ScriptParser:
    @classmethod
    def parse_script_entry(cls, script_entry: dict[str, Any]) -> ScriptEntry:
        if ScriptKeyword.SCRIPT not in script_entry:
            raise ConfigError("Missing '_script' key in script entry")

        script_ref = script_entry[ScriptKeyword.SCRIPT]
        if "::" not in script_ref:
            raise ConfigValidationError(f"Invalid script reference: {script_ref}")

        script_path_str, func_name = script_ref.split("::", 1)
        script_path = Path(script_path_str)

        if script_path.suffix == "":
            candidate = script_path.with_suffix(".py")
            if candidate.exists():
                script_path = candidate

        reader = ScriptReaderFactory.get_reader(script_path)
        func = reader.get_function(func_name.strip())

        reload_targets_value = script_entry.get(ScriptKeyword.RELOAD, "")
        if not isinstance(reload_targets_value, str):
            raise ConfigValidationError("_reload must be comma separated string")

        reload_targets = cls.parse_reload_targets(reload_targets_value)

        refresh_value = script_entry.get(ScriptKeyword.REFRESH)
        refresh = cls.parse_refresh(refresh_value or "on Startup")
        context = {k: v for k, v in script_entry.items() if not k.startswith("_")}

        return ScriptEntry(
            name=func_name.strip(),
            func=func,
            reload_targets=reload_targets,
            refresh=refresh,
            context=context,
        )

    @classmethod
    def parse_refresh(cls, refresh: str) -> RefreshConfig:
        if refresh.startswith("every"):
            interval = cls.parse_refresh_interval(refresh)
            return RefreshConfig(kind=RefreshKind.INTERVAL, value=interval)

        if refresh.startswith("on"):
            event_cls = cls.parse_event(refresh)
            return RefreshConfig(kind=RefreshKind.EVENT, value=event_cls)

        raise ConfigValidationError(f"Invalid refresh config: '{refresh}'. ")

    @classmethod
    def parse_refresh_interval(cls, refresh: str) -> int:
        match = re.match(r"^every\s+(\d+)\s*([smh])$", refresh.strip())
        if not match:
            raise ConfigValidationError(
                f"Invalid refresh interval format: '{refresh}'. "
                f"Expected format: 'every <amount><unit>', e.g. 'every 5m' or 'every 30s'."
            )

        amount = int(match.group(1))
        unit = match.group(2)
        multipliers = {"s": 1, "m": 60, "h": 3600}
        return amount * multipliers[unit]

    @classmethod
    def parse_event(cls, refresh: str) -> type["DooitEvent"]:
        name = refresh.replace("on", "", 1).strip()
        if not name:
            raise ConfigValidationError("Event name cannot be empty in refresh config")

        from dooit.ui.bridge import events as events_module

        event = getattr(events_module, name, None)
        if event is None:
            raise ConfigValidationError(f"Event '{name}' not found for refresh config")

        return event

    @classmethod
    def parse_reload_targets(cls, reload_value: Optional[str]) -> set[str]:
        if not reload_value:
            return set()

        return {item.strip() for item in reload_value.split(",") if item.strip()}
