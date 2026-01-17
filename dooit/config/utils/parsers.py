import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.events import DooitEvent


def parse_refresh_interval(refresh: str) -> Optional[float]:
    """Parse 'every 5s|5m|5h' into seconds."""
    match = re.match(r"^every\s+(\d+)\s*([smh])$", refresh.strip())
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)
    multipliers = {"s": 1, "m": 60, "h": 3600}
    return amount * multipliers[unit]


def parse_event(refresh: str) -> Optional[type["DooitEvent"]]:
    """Parse 'on EventName' into the event class."""
    name = refresh.replace("on", "", 1).strip()
    if not name:
        return None

    from dooit.ui.api import events as events_module

    return getattr(events_module, name, None)


def parse_reload_targets(reload_value: Optional[str]) -> set[str]:
    """Parse comma-separated reload targets into a set."""
    if not reload_value:
        return set()
    return {item.strip() for item in reload_value.split(",") if item.strip()}
