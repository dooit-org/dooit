"""
How a day is written out wherever the app spells one

One convention, shared by the date columns and by the day headings of the
Upcoming project, so a date reads the same whichever of them it turns up in.
"""

from datetime import date

# Austrian German weekday abbreviations, indexed by `date.weekday()`. Spelled
# out here rather than left to `%a`, which follows the process locale and would
# give English names on a default install.
WEEKDAY_NAMES = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")

# German date convention: day first, dot separated, and the year always
# spelled out as its last two digits
DATE_FORMAT = "%d.%m.%y"


def day_label(day: date) -> str:
    """A day as weekday and date, the way every date in the app is written"""

    return f"{WEEKDAY_NAMES[day.weekday()]}, {day.strftime(DATE_FORMAT)}"
