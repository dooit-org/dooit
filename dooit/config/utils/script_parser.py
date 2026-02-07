import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.events import DooitEvent

from .script_reader import ScriptReader


class RefreshKind(str, Enum):
    INTERVAL = "interval"
    EVENT = "event"


@dataclass(frozen=True)
class RefreshConfig:
    kind: RefreshKind
    value: int | type["DooitEvent"]


@dataclass
class ScriptEntry:
    name: str
    func: Callable
    reload_targets: set[str] = field(default_factory=set)
    refresh: Optional["RefreshConfig"] = None


class ScriptReaderFactory:
    _cache = {}

    @classmethod
    def get_reader(cls, path: Path) -> ScriptReader:
        resolved_path = path.resolve()
        if resolved_path not in cls._cache:
            cls._cache[resolved_path] = ScriptReader(resolved_path)
        return cls._cache[resolved_path]


class ScriptParser:
    @classmethod
    def parse_script_entry(
        cls, base_path: Path, script_ref: str, config_data: dict
    ) -> ScriptEntry:
        if "::" not in script_ref:
            raise ValueError(f"Invalid script reference: {script_ref}")

        script_path_str, func_name = script_ref.split("::", 1)
        script_path = Path(script_path_str)
        if not script_path.is_absolute():
            script_path = (base_path.parent / script_path).resolve()

        if script_path.suffix == "":
            candidate = script_path.with_suffix(".py")
            if candidate.exists():
                script_path = candidate

        reader = ScriptReaderFactory.get_reader(script_path)
        func = reader.get_function(func_name.strip())

        reload_targets = set()
        reload_targets_value = config_data.get("reload_targets")
        if isinstance(reload_targets_value, (set, list, tuple)):
            reload_targets = set(reload_targets_value)

        refresh_value = config_data.get("_refresh")
        refresh = None
        if isinstance(refresh_value, str):
            refresh = cls.parse_refresh(refresh_value)

        return ScriptEntry(
            name=func_name.strip(),
            func=func,
            reload_targets=reload_targets,
            refresh=refresh,
        )

    @classmethod
    def parse_refresh(cls, refresh: str) -> Optional[RefreshConfig]:
        if refresh.startswith("every"):
            interval = cls.parse_refresh_interval(refresh)
            if interval is None:
                return None
            return RefreshConfig(kind=RefreshKind.INTERVAL, value=interval)

        if refresh.startswith("on"):
            event_cls = cls.parse_event(refresh)
            if event_cls is None:
                return None
            return RefreshConfig(kind=RefreshKind.EVENT, value=event_cls)

        return None

    @classmethod
    def parse_refresh_interval(cls, refresh: str) -> Optional[float]:
        """Parse 'every 5s|5m|5h' into seconds."""
        match = re.match(r"^every\s+(\d+)\s*([smh])$", refresh.strip())
        if not match:
            return None

        amount = int(match.group(1))
        unit = match.group(2)
        multipliers = {"s": 1, "m": 60, "h": 3600}
        return amount * multipliers[unit]

    @classmethod
    def parse_event(cls, refresh: str) -> Optional[type["DooitEvent"]]:
        """Parse 'on EventName' into the event class."""
        name = refresh.replace("on", "", 1).strip()
        if not name:
            return None

        from dooit.ui.api import events as events_module

        return getattr(events_module, name, None)

    @classmethod
    def parse_reload_targets(cls, reload_value: Optional[str]) -> set[str]:
        """Parse comma-separated reload targets into a set."""
        if not reload_value:
            return set()
        return {item.strip() for item in reload_value.split(",") if item.strip()}
