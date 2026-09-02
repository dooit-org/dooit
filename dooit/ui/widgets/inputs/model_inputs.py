import re
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

from rich.style import Style
from rich.text import Text

from .simple_input import SimpleInput
from dooit.api import Todo, Workspace
from dooit.api.theme import DooitThemeBase
from dooit.api.todo import MAX_EFFORT
from dooit.utils import parse


class TodoDescription(SimpleInput[Todo, str]):
    @property
    def _property(self) -> str:
        return "description"


class WorkspaceDescription(SimpleInput[Workspace, str]):
    @property
    def _property(self) -> str:
        return "description"


class WorkspaceTasks(SimpleInput[Workspace, int]):
    """
    How many todos are nested under the workspace; derived, so never editable
    """

    editable = False

    @property
    def _property(self) -> str:
        return "total_todos"

    @property
    def value(self) -> str:
        # Counted on every render: todos come and go while the renderer stays
        count = self.model_value

        if not count:
            return ""

        return str(count)


class DateInput(SimpleInput[Todo, datetime]):
    """
    A column holding a single date: the deadline, or the day planned for it
    """

    # Day first, to match both the column's German rendering and the way the
    # parser reads an ambiguous `5.9`, so what is shown can be typed back in
    EDIT_FORMAT = "%d.%m.%Y"

    @classmethod
    def _format(cls, value: datetime) -> str:
        dt_format = cls.EDIT_FORMAT

        if value.hour or value.minute:
            dt_format += " %H:%M"

        return value.strftime(dt_format)

    def _get_default_value(self) -> str:
        value = self.model_value

        if value is None:
            return ""

        return self._format(value)

    def _typecast_value(self, value: str) -> Any:
        if not value.strip():
            return None

        date, ok = parse(value)
        if not ok:
            # Raised rather than swallowed, so that the tree turns it into a
            # notification instead of silently dropping what was typed
            raise ValueError(f'Could not understand {self._property} date: "{value}"')

        return date

    def render_editing(self, theme: DooitThemeBase) -> Text:
        """
        The buffer, plus what the text currently in it resolves to
        """

        text = Text(self.draw().strip())

        if not self.value.strip():
            return text

        date, ok = parse(self.value)

        if not ok:
            hint, color = "?", theme.red
        elif date is None:
            hint, color = "no date", theme.green
        else:
            hint, color = self._format(date), theme.green

        return text + Text(f" → {hint}", style=Style(color=color, dim=True))


class Due(DateInput):
    """
    The date the todo has to be done by
    """


class Scheduled(DateInput):
    """
    The date the todo is planned to be worked on
    """


class Priority(SimpleInput[Todo, int]):
    @property
    def value(self) -> str:
        res = self.model.priority

        if res == 0:
            return ""

        return str(self.model.priority)

    def _typecast_value(self, value: str) -> Any:
        if not value or value == "0":
            return 0

        return int(value)


class Effort(SimpleInput[Todo, int]):
    def _typecast_value(self, value: str) -> Any:
        # Anything that isn't a number on the scale clears the effort, rather
        # than throwing out of the edit and leaving the todo half-updated
        if not value.isdigit():
            return 0

        return min(int(value), MAX_EFFORT)


class Status(SimpleInput[Todo, str]):
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
    @staticmethod
    def parse_recurrence(recurrence: str) -> timedelta:
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
