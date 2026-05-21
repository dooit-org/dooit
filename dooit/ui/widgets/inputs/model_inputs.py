import re
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

from .simple_input import SimpleInput
from dooit.api import Todo, Workspace
from dooit.utils import parse


class TodoDescription(SimpleInput[Todo, str]):
    """Input widget for editing a Todo item's description."""

    @property
    def _property(self) -> str:
        return "description"


class WorkspaceDescription(SimpleInput[Workspace, str]):
    """Input widget for editing a Workspace item's description."""

    @property
    def _property(self) -> str:
        return "description"


class Due(SimpleInput[Todo, datetime]):
    """Input widget for editing a Todo item's due date."""

    def _get_default_value(self) -> str:
        value = self.model_value

        if value is None:
            return ""

        if value.hour or value.minute:
            return self.model_value.strftime("%Y-%m-%d %H:%M")

        return value.strftime("%Y-%m-%d")

    def _typecast_value(self, value: str) -> Any:
        if not value:
            return None

        due, ok = parse(value)
        if not ok:
            return self.model_value

        return due


class Urgency(SimpleInput[Todo, int]):
    """Input widget for editing a Todo item's urgency level."""

    @property
    def value(self) -> str:
        """Return the urgency as a string, or empty string if zero."""
        res = self.model.urgency

        if res == 0:
            return ""

        return str(self.model.urgency)

    def _typecast_value(self, value: str) -> Any:
        if not value or value == "0":
            return 0

        return int(value)


class Effort(SimpleInput[Todo, int]):
    """Input widget for editing a Todo item's effort estimate."""

    def _typecast_value(self, value: str) -> Any:
        if not value or value == "0":
            return 0

        return int(value)


class Status(SimpleInput[Todo, str]):
    """Input widget for displaying and toggling a Todo item's completion status."""

    def _get_default_value(self) -> str:
        val = self.model_value

        if val == "completed":
            return "x"

        if val == "overdue":
            return "!"

        return "o"

    def _typecast_value(self, value: str) -> Any:
        if value == "COMPLETED":
            return False

        return True


class Recurrence(SimpleInput[Todo, timedelta]):
    """Input widget for editing a Todo item's recurrence interval."""

    @staticmethod
    def parse_recurrence(recurrence: str) -> timedelta:
        """Parse a recurrence string like '2d' or '1w' into a timedelta."""
        DURATION_LEGEND = {
            "m": "minute",
            "h": "hour",
            "d": "day",
            "w": "week",
        }

        def split_duration(duration: str) -> Tuple[str, str]:
            if re.match(r"^(\d+)[mhdw]$", duration):
                return duration[-1], duration[:-1]
            else:
                raise ValueError("Invalid recurrence format")

        sign, frequency = split_duration(recurrence)
        frequency = int(frequency)
        return timedelta(**{f"{DURATION_LEGEND[sign]}s": frequency})

    def _typecast_value(self, value: str) -> Optional[timedelta]:
        if not value:
            return None

        return self.parse_recurrence(value)

    @staticmethod
    def timedelta_to_simple_string(td: timedelta):
        """Convert a timedelta to a compact string like '2d', '1w', '3h', or '5m'."""
        if td.days >= 7 and td.days % 7 == 0:
            weeks = td.days // 7
            return f"{weeks}w"
        elif td.days > 0:
            return f"{td.days}d"
        elif td.seconds >= 3600:
            hours = td.seconds // 3600
            return f"{hours}h"
        elif td.seconds >= 60:
            minutes = td.seconds // 60
            return f"{minutes}m"

        return "?"

    def _get_default_value(self) -> str:
        value = self.model_value

        if value is None:
            return ""

        return self.timedelta_to_simple_string(value)
