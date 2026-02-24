from collections import defaultdict
from typing import Callable, cast

from dooit.config.config import ScriptField
from dooit.config.script_parser import RefreshKind
from dooit.ui.bridge.events import DooitEvent, TimerEvent


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

        self._event_triggers: dict[type[DooitEvent], list[ScriptField]] = defaultdict(
            list
        )
        self._time_triggers: dict[int, list[ScriptField]] = defaultdict(list)
        self.setup_scripts()

    def setup_scripts(self):
        for _, script in self.scripts.items():
            refresh = script.entry.refresh

            if not refresh:
                continue

            if refresh.kind == RefreshKind.EVENT:
                assert isinstance(refresh.value, type) and issubclass(
                    refresh.value, DooitEvent
                )
                event_cls = cast(type[DooitEvent], refresh.value)

                self._event_triggers[event_cls].append(script)

            elif refresh.kind == RefreshKind.INTERVAL:
                assert isinstance(refresh.value, int)
                self._time_triggers[refresh.value].append(script)

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
            params = {}

            if not isinstance(event, TimerEvent):
                params |= {"event": event}

            entry.update(**params)
            for callback in self.reload_entries.values():
                callback()
