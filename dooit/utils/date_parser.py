"""
Natural language due date parsing, in the style of Todoist.

Accepts the shorthand people actually type -- ``tom``, ``next monday``,
``in one week``, ``1d``, ``tom 16:00`` -- and falls back to ``dateutil`` for
anything absolute.
"""

import re
from calendar import monthrange
from datetime import datetime, time
from typing import Optional, Tuple

from dateutil import parser
from dateutil.relativedelta import relativedelta

# Ambiguous numeric dates read day first (`5.9` is 5 September), matching the
# German format the due column is rendered in. ISO input is unaffected:
# dateutil recognises `2026-09-05` on its own.
DAY_FIRST = True

WEEKDAYS = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

SATURDAY = 5

# Todoist's day parts, and the times it resolves them to
DAY_PARTS = {
    "morning": time(9),
    "noon": time(12),
    "afternoon": time(12),
    "evening": time(19),
    "night": time(22),
}

# `m` is minutes rather than months, so that this agrees with the recurrence
# field's own `1m`/`2h`/`3d`/`4w` legend. Months are spelled `mo`.
UNITS = {
    "m": "minutes",
    "min": "minutes",
    "mins": "minutes",
    "minute": "minutes",
    "minutes": "minutes",
    "h": "hours",
    "hr": "hours",
    "hrs": "hours",
    "hour": "hours",
    "hours": "hours",
    "d": "days",
    "day": "days",
    "days": "days",
    "w": "weeks",
    "wk": "weeks",
    "wks": "weeks",
    "week": "weeks",
    "weeks": "weeks",
    "mo": "months",
    "mon": "months",
    "mos": "months",
    "month": "months",
    "months": "months",
    "y": "years",
    "yr": "years",
    "yrs": "years",
    "year": "years",
    "years": "years",
}

NUMBER_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

# Words that only ever join two halves of an expression -- "tomorrow at 16:00"
# means the same thing as "tomorrow 16:00"
FILLER_WORDS = {"at", "on", "@"}

CLEAR_WORDS = {"no date", "no due date", "none", "never", "-"}

# 24h with a colon, or a 12h time with am/pm. Colon-less times ("1600", "16h")
# are deliberately not matched: Todoist rejects them too, matching them would
# swallow the day of a date like "16 jan", and it leaves `16h` free to mean an
# offset, the same as `1d` and `2w` do.
# The am/pm form is tried first, or the bare 24h pattern would take the "4:30"
# out of "4:30pm" and leave the meridiem behind as unparseable text
TIME_PATTERNS = (
    re.compile(r"(?<![\d:.])(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b"),
    re.compile(r"(?<![\d:.])(\d{1,2}):(\d{2})(?![\d:])"),
)

# `dayfirst` reorders the month and day of an ISO date too, so ISO input is
# routed around it -- it is already unambiguous
ISO_DATE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}")

# German numeric dates. The trailing dot is part of how they are written
# ("19.07."), and the year is routinely left off entirely.
DOTTED_DATE = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\.(\d{2}|\d{4}))?\.?$")
DOTTED_MONTH_YEAR = re.compile(r"^(\d{1,2})\.(\d{4})\.?$")
DOTTED_DAY = re.compile(r"^(\d{1,2})\.$")

# Anything built only of digits and dots is meant as one of the forms above.
# When it is not one of them it is a typo, and dateutil's guess at it is not
# worth having -- it reads `1..2` as 1 February and `19.07.123` as the year 123.
DOTTED_SHAPE = re.compile(r"^(?=.*\.)[\d.]+$")

SHORTHAND = re.compile(r"^\+?(\d+)\s*([a-z]+)$")
IN_OFFSET = re.compile(r"^in\s+(\d+|[a-z]+)\s*([a-z]+)$")


# The words a date expression is allowed to open with. What they are for is
# picking a date out of a line that is mostly not one: a span of words is only
# worth handing to `parse` when it starts with something the grammar above
# could actually read, or a bare "5" counted out of a description would come
# back as the fifth of the month.
DATE_STARTERS = (
    {
        "today",
        "tod",
        "tomorrow",
        "tom",
        "tmr",
        "tmrw",
        "tmw",
        "yesterday",
        "yest",
        "yd",
        "someday",
        "weekend",
        "weekday",
        "next",
        "mid",
        "in",
        "end",
        "eom",
    }
    | set(WEEKDAYS)
    | set(MONTHS)
    | set(DAY_PARTS)
)

# The words above that are ordinary English besides being dates, and so are
# not read as a date when they are the whole of the expression. Each of them
# has a spelling that is not ("saturday" for "sat"), and each still reads as a
# date the moment it is given something to modify ("friday evening", "may 5").
AMBIGUOUS_ALONE = {"may", "sat", "sun"} | set(DAY_PARTS)


class _Ambiguous(Exception):
    """A pattern matched the shape but not the vocabulary; keep looking."""


def _strip_time(text: str) -> Tuple[str, Optional[time]]:
    """
    Pulls a time off the expression, returning the rest of it and that time.
    """

    for word, value in DAY_PARTS.items():
        stripped = re.sub(rf"\b{word}\b", " ", text)
        if stripped != text:
            return _squash(stripped), value

    for pattern in TIME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        groups = match.groups()
        hour = int(groups[0])
        minute = int(groups[1]) if len(groups) > 1 and groups[1] else 0

        if len(groups) == 3:  # the am/pm form
            if groups[2] == "pm" and hour != 12:
                hour += 12
            elif groups[2] == "am" and hour == 12:
                hour = 0

        if hour > 23 or minute > 59:
            continue

        rest = text[: match.start()] + " " + text[match.end() :]
        return _squash(rest), time(hour, minute)

    return text, None


def _squash(text: str) -> str:
    return " ".join(text.split())


def _normalize(value: str) -> str:
    text = _squash(value.lower())

    # The due column renders the time in parens, so the displayed form can be
    # typed straight back in
    text = text.replace("(", " ").replace(")", " ")
    return _squash(text)


def looks_like_date_start(word: str, alone: bool = False) -> bool:
    """
    Whether a word could be the first of a date expression

    A loose test on purpose: all it says is that a span is worth trying, and
    `parse` is what decides whether it means anything. What it rules out is
    the ordinary words of a description, which is the whole point of asking.

    `alone` says the word would be the whole of the expression, which is where
    the shorthand stops being worth its false readings: "sat in the meeting"
    and "may need a look" are not dates, and neither is the "evening" of an
    evening class. Spelled out, or modifying something -- "saturday", "friday
    evening" -- they are read as dates as they always were.
    """

    text = _normalize(word)

    if not text:
        return False

    if alone and text in AMBIGUOUS_ALONE:
        return False

    if text in DATE_STARTERS:
        return True

    return bool(
        SHORTHAND.match(text)
        or ISO_DATE.match(text)
        or DOTTED_SHAPE.match(text)
        or any(pattern.match(text) for pattern in TIME_PATTERNS)
    )


def _drop_filler(text: str) -> str:
    words = [w for w in text.split() if w not in FILLER_WORDS]
    return " ".join(words)


def _next_weekday(start: datetime, weekday: int, allow_today: bool) -> datetime:
    delta = (weekday - start.weekday()) % 7

    if delta == 0 and not allow_today:
        delta = 7

    return start + relativedelta(days=delta)


# An offset in days or larger lands on a bare date, so it counts from midnight;
# one in hours or minutes is meant as "from now", so it counts from the clock.
CLOCK_UNITS = ("minutes", "hours")


def _offset(today: datetime, now: datetime, count: int, unit: str) -> datetime:
    start = now if unit in CLOCK_UNITS else today
    return start + relativedelta(**{unit: count})


def _keyword_date(text: str, today: datetime, now: datetime) -> Optional[datetime]:
    """
    Resolves the date half of an expression, with the time already stripped off.

    Returns None when nothing in the grammar matches, leaving the caller to try
    an absolute parse.
    """

    if not text:
        # Only a time was given, so it belongs to today
        return today

    if text in ("today", "tod"):
        return today

    if text in ("tomorrow", "tom", "tmr", "tmrw", "tmw"):
        return today + relativedelta(days=1)

    if text in ("yesterday", "yest", "yd"):
        return today - relativedelta(days=1)

    if text == "someday":
        return today + relativedelta(months=2)

    if text in ("end of month", "eom", "end of the month"):
        last = monthrange(today.year, today.month)[1]
        return today.replace(day=last)

    if text in ("weekend", "this weekend"):
        return _next_weekday(today, SATURDAY, allow_today=False)

    if text in ("weekday", "next weekday"):
        current = today + relativedelta(days=1)
        while current.weekday() >= SATURDAY:
            current += relativedelta(days=1)
        return current

    if text in WEEKDAYS:
        return _next_weekday(today, WEEKDAYS[text], allow_today=True)

    if text.startswith("next "):
        rest = text[5:]

        if rest == "week":
            # The Monday that starts next week, which is what Todoist means by
            # it -- "in one week" is the one that means seven days from now
            return _next_weekday(today, 0, allow_today=False)

        if rest == "month":
            return (today + relativedelta(months=1)).replace(day=1)

        if rest == "year":
            return today.replace(year=today.year + 1, month=1, day=1)

        if rest == "weekend":
            saturday = _next_weekday(today, SATURDAY, allow_today=False)
            return saturday

        if rest in WEEKDAYS:
            # A week on from the coming one
            coming = _next_weekday(today, WEEKDAYS[rest], allow_today=False)
            return coming + relativedelta(days=7)

    if text.startswith("mid "):
        month = text[4:]
        if month in MONTHS:
            return _mid_month(today, MONTHS[month])

    match = IN_OFFSET.match(text)
    if match:
        count, unit = match.groups()
        if unit not in UNITS:
            raise _Ambiguous()

        if count.isdigit():
            amount = int(count)
        elif count in NUMBER_WORDS:
            amount = NUMBER_WORDS[count]
        else:
            raise _Ambiguous()

        return _offset(today, now, amount, UNITS[unit])

    match = SHORTHAND.match(text)
    if match:
        count, unit = match.groups()
        if unit in UNITS:
            return _offset(today, now, int(count), UNITS[unit])

    return None


def _mid_month(today: datetime, month: int) -> datetime:
    year = today.year if month >= today.month else today.year + 1
    return today.replace(year=year, month=month, day=15)


def _expand_year(year: Optional[str], today: datetime) -> int:
    if year is None:
        # German dates are routinely written without one -- "19.07." is this
        # year, the same way `jan 1` already resolves to this year
        return today.year

    if len(year) == 2:
        return 2000 + int(year)

    return int(year)


def _build(year: int, month: int, day: int, today: datetime) -> datetime:
    try:
        return today.replace(year=year, month=month, day=day)
    except ValueError:
        # A real calendar impossibility -- 32.01. or 29.02. in a common year
        raise _Ambiguous()


def _numeric_date(text: str, today: datetime) -> Optional[datetime]:
    """
    Dot separated dates, the way they are written in German.

    dateutil cannot be trusted with these: it reads a trailing dot as a parse
    error and a bare `19.07` as the 19th of the *current* month, silently
    throwing the month away. Both are handled here instead.
    """

    match = DOTTED_DATE.match(text)
    if match:
        day, month, year = match.groups()
        return _build(_expand_year(year, today), int(month), int(day), today)

    match = DOTTED_MONTH_YEAR.match(text)
    if match:
        month, year = match.groups()
        return _build(int(year), int(month), 1, today)

    match = DOTTED_DAY.match(text)
    if match:
        return _build(today.year, today.month, int(match.group(1)), today)

    if DOTTED_SHAPE.match(text):
        raise _Ambiguous()

    return None


def _absolute(text: str, today: datetime) -> Optional[datetime]:
    dayfirst = DAY_FIRST and not ISO_DATE.match(text)

    try:
        return parser.parse(text, dayfirst=dayfirst, default=today)
    except (parser.ParserError, ValueError, OverflowError, TypeError):
        return None


def parse(
    value: str, now: Optional[datetime] = None
) -> Tuple[Optional[datetime], bool]:
    """
    Turns a due date expression into a datetime.

    Returns the datetime and whether the expression was understood at all.
    ``(None, True)`` means the expression explicitly asked for no date;
    ``(None, False)`` means it could not be parsed.
    """

    now = now or datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    text = _normalize(value)

    if not text:
        return None, True

    if text in CLEAR_WORDS:
        return None, True

    text, at = _strip_time(text)
    text = _drop_filler(text)

    try:
        date = _keyword_date(text, today, now)

        if date is None:
            date = _numeric_date(text, today)
    except _Ambiguous:
        return None, False

    if date is None:
        date = _absolute(text, today)

    if date is None:
        return None, False

    if at is not None:
        date = date.replace(hour=at.hour, minute=at.minute)

    # An offset counted off the clock ("in 2 hours") carries the current seconds
    # along with it, which is noise on a due date
    return date.replace(second=0, microsecond=0), True
