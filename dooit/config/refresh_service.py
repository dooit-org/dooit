from collections import defaultdict
from typing import Callable

from dooit.config.config import ScriptField
from dooit.config.script_parser import (
    EventRefresh,
    IntervalRefresh,
    KeyRefresh,
)
from dooit.ui.bridge.events import DooitEvent, TimerEvent


class EventDict(dict[type[DooitEvent], list[ScriptField]]):
    """
    A special dict that matches the key by event subclassing
    For example if Event B is subclass of Event A
    And if Event B happens
    The subscriber to Event A also gets returned
    """

    def add(self, event_cls: type[DooitEvent], value: ScriptField) -> None:
        self.setdefault(event_cls, []).append(value)

    def __getitem__(self, event_cls: type[DooitEvent]) -> list[ScriptField]:
        matched: list[ScriptField] = []
        for registered_cls, values in self.items():
            if issubclass(event_cls, registered_cls):
                matched.extend(values)
        return matched


class RefreshService:
    """
    Manages script wrappers, __dooit_value caching, timer/event registration,
    and dispatches ui_refresh() to registered targets.
    """

    def __init__(
        self,
        scripts: dict[str, ScriptField],
        reload_entries: dict[str, Callable],
    ) -> None:
        self.scripts = scripts
        self.reload_entries = reload_entries

        self._event_triggers: EventDict = EventDict()
        self._time_triggers: dict[int, list[ScriptField]] = defaultdict(list)
        self._key_triggers: dict[str, list[ScriptField]] = defaultdict(list)
        self.setup_scripts()

    def setup_scripts(self):
        for script in self.scripts.values():
            refresh = script.entry.refresh
            match refresh:
                case EventRefresh(event=event_cls):
                    self._event_triggers.add(event_cls, script)
                case IntervalRefresh(seconds=seconds):
                    self._time_triggers[seconds].append(script)
                case KeyRefresh(key=key):
                    self._key_triggers[key].append(script)

    def trigger_event(self, event: DooitEvent) -> None:
        """Trigger scripts registered to an event."""

        if isinstance(event, TimerEvent):
            entries = []
            for interval in self._time_triggers.keys():
                if event.second % interval == 0:
                    entries.extend(self._time_triggers[interval])
        else:
            entries = self._event_triggers[type(event)]

        for entry in entries:
            entry.update(event=event)
            reload_targets = entry.entry.reload_targets
            for target in reload_targets:
                callback = self.reload_entries[target]
                callback()
