from typing import Protocol, cast, runtime_checkable

from dooit.config.config import ScriptField
from dooit.config.script_parser import RefreshKind, ScriptEntry
from dooit.ui.bridge.events import DooitEvent, Startup, TimerEvent


@runtime_checkable
class Refreshable(Protocol):
    def ui_refresh(self) -> None: ...


class RefreshService:
    """
    Manages script wrappers, __dooit_value caching, timer/event registration,
    and dispatches ui_refresh() to registered targets.
    """

    def __init__(
        self,
        scripts: dict[str, ScriptField],
        reload_entries: dict[str, Refreshable],
    ) -> None:
        self.scripts = scripts
        self.reload_entries = reload_entries

        self._event_triggers: dict[type[DooitEvent], ScriptEntry] = {}
        self._time_triggers: dict[int, ScriptEntry] = {}
        self.setup_scripts()

    def setup_scripts(self):
        for _, script in self.scripts.items():
            refresh = script.entry.refresh
            self._event_triggers[Startup] = script.entry

            if not refresh:
                continue

            if refresh.kind == RefreshKind.EVENT:
                assert isinstance(refresh.value, type) and issubclass(
                    refresh.value, DooitEvent
                )
                event_cls = cast(type[DooitEvent], refresh.value)

                self._event_triggers[event_cls] = script.entry

            elif refresh.kind == RefreshKind.INTERVAL:
                assert isinstance(refresh.value, int)
                self._time_triggers[refresh.value] = script.entry

    def trigger_event(self, event: DooitEvent) -> None:
        """Trigger scripts registered to an event."""

        entry = self._event_triggers.get(type(event))
        params = {}

        if not isinstance(event, TimerEvent):
            params |= {"event": event}

        if entry:
            entry.call(**params)
            for targets in self.reload_entries.values():
                targets.ui_refresh()
