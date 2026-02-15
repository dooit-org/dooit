from functools import partial
from collections import defaultdict
from typing import TYPE_CHECKING, Callable, List, Type

from dooit.ui.api.events import DooitEvent

DOOIT_EVENT_ATTR = "__dooit_event"
DOOIT_TIMER_ATTR = "__dooit_timer"

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


class PluginManager:
    def __init__(self, api: "DooitAPI") -> None:
        self.events: defaultdict[Type[DooitEvent], List[Callable]] = defaultdict(list)
        self.timers: defaultdict[float, List[Callable]] = defaultdict(list)
        self.api = api
        self.app = api.app

    def _dispatch(self, obj: Callable, *params) -> None:
        """Call the registered handler. The handler owns caching and rerendering."""
        obj(self.api, *params)

    def on_event(self, event: DooitEvent):
        matched_events = [
            e for e in self.events.keys() if issubclass(event.__class__, e)
        ]

        for e in matched_events:
            for obj in self.events[e]:
                self._dispatch(obj, event)

    def _register_events(self, events: List[Type[DooitEvent]], obj: Callable):
        for event in events:
            self.events[event].append(obj)

    def _register_timer(self, obj: Callable):
        if interval := getattr(obj, DOOIT_TIMER_ATTR, None):
            func = partial(self._dispatch, obj)
            func()
            self.api.app.set_interval(interval, func)

    def register(self, obj):
        if event := getattr(obj, DOOIT_EVENT_ATTR, None):
            return self._register_events(event, obj)

        if getattr(obj, DOOIT_TIMER_ATTR, None):
            return self._register_timer(obj)
