import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from dooit.ui.bridge.events import DooitEvent
from dooit.utils import PyScriptReader


class ScriptKeyword(str, Enum):
    SCRIPT = "_script"
    REFRESH = "_refresh"
    RELOAD_TARGETS = "reload_targets"


class RefreshKind(str, Enum):
    INTERVAL = "interval"
    EVENT = "event"


@dataclass(frozen=True)
class RefreshConfig:
    kind: RefreshKind
    value: int | type[DooitEvent]


@dataclass
class ScriptEntry:
    name: str
    func: Callable
    reload_targets: set[str] = field(default_factory=set)
    refresh: Optional["RefreshConfig"] = None
    context: dict = field(default_factory=dict)

    def call(self, **params):
        return self.func(**params, context=self.context)


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
            raise ValueError("Missing '_script' key in script entry")

        script_ref = script_entry[ScriptKeyword.SCRIPT]
        if "::" not in script_ref:
            raise ValueError(f"Invalid script reference: {script_ref}")

        script_path_str, func_name = script_ref.split("::", 1)
        script_path = Path(script_path_str)

        if script_path.suffix == "":
            candidate = script_path.with_suffix(".py")
            if candidate.exists():
                script_path = candidate

        reader = ScriptReaderFactory.get_reader(script_path)
        func = reader.get_function(func_name.strip())

        reload_targets_value = script_entry.get(ScriptKeyword.RELOAD_TARGETS, [])
        assert isinstance(reload_targets_value, Iterable), (
            "reload_targets must be an iterable of strings"
        )

        reload_targets = set(reload_targets_value)

        refresh_value = script_entry.get(ScriptKeyword.REFRESH)
        refresh = cls.parse_refresh(refresh_value) if refresh_value else None
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

        raise ValueError(f"Invalid refresh config: '{refresh}'. ")

    @classmethod
    def parse_refresh_interval(cls, refresh: str) -> int:
        match = re.match(r"^every\s+(\d+)\s*([smh])$", refresh.strip())
        if not match:
            raise ValueError(
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
        assert bool(name), "Event name cannot be empty in refresh config"

        from dooit.ui.bridge import events as events_module

        event = getattr(events_module, name, None)
        assert event is not None, f"Event '{name}' not found for refresh config"

        return event

    @classmethod
    def parse_reload_targets(cls, reload_value: Optional[str]) -> set[str]:
        if not reload_value:
            return set()
        return {item.strip() for item in reload_value.split(",") if item.strip()}
