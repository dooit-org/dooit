from datetime import datetime
import unittest
from dooit.utils.date_parser import parse

# A Wednesday, so that "next monday" and a bare weekday are visibly different
NOW = datetime(2026, 9, 2, 10, 30)


def at(year=2026, month=9, day=2, hour=0, minute=0) -> datetime:
    return datetime(year, month, day, hour, minute)


class TestDateParse(unittest.TestCase):
    def test_parsers(self):
        # normal format date
        assert parse("2020-01-01") == (datetime(2020, 1, 1), True)

        # invalid date
        assert parse("?????") == (None, False)

        # english date formats
        assert parse("july 1 2034") == (datetime(2034, 7, 1), True)
        assert parse("jan 1") == (datetime(datetime.now().year, 1, 1), True)

    def test_relative_days(self):
        assert parse("today", NOW) == (at(), True)
        assert parse("tod", NOW) == (at(), True)
        assert parse("tomorrow", NOW) == (at(day=3), True)
        assert parse("tom", NOW) == (at(day=3), True)
        assert parse("yesterday", NOW) == (at(day=1), True)

    def test_case_and_spacing_are_ignored(self):
        assert parse("  ToMoRRoW  ", NOW) == (at(day=3), True)

    def test_times(self):
        assert parse("tom 16:00", NOW) == (at(day=3, hour=16), True)
        assert parse("tomorrow at 16:00", NOW) == (at(day=3, hour=16), True)
        assert parse("tom 4pm", NOW) == (at(day=3, hour=16), True)
        assert parse("tom 4:30pm", NOW) == (at(day=3, hour=16, minute=30), True)
        assert parse("16:00", NOW) == (at(hour=16), True)

        # the day parts Todoist resolves to fixed hours
        assert parse("tom morning", NOW) == (at(day=3, hour=9), True)
        assert parse("tom evening", NOW) == (at(day=3, hour=19), True)

        # the form the due column renders, typed straight back in
        assert parse("05.09.26 (16:00)", NOW) == (at(day=5, hour=16), True)

    def test_shorthand_offsets(self):
        assert parse("1d", NOW) == (at(day=3), True)
        assert parse("2d", NOW) == (at(day=4), True)
        assert parse("+3w", NOW) == (at(day=23), True)
        assert parse("6mo", NOW) == (at(year=2027, month=3), True)
        assert parse("1y", NOW) == (at(year=2027), True)

    def test_in_offsets(self):
        assert parse("in 5 days", NOW) == (at(day=7), True)
        assert parse("in one week", NOW) == (at(day=9), True)
        assert parse("in 3 weeks", NOW) == (at(day=23), True)

        # hours and minutes are meant as "from now", so they keep the clock
        assert parse("in 2 hours", NOW) == (at(hour=12, minute=30), True)
        assert parse("30m", NOW) == (at(hour=11, minute=0), True)

    def test_next_periods(self):
        # the Monday that starts next week, unlike "in one week"
        assert parse("next week", NOW) == (at(day=7), True)
        assert parse("next month", NOW) == (at(month=10, day=1), True)
        assert parse("next year", NOW) == (at(year=2027, month=1, day=1), True)

    def test_weekdays(self):
        # a bare weekday is the coming one
        assert parse("friday", NOW) == (at(day=4), True)
        assert parse("fri", NOW) == (at(day=4), True)
        assert parse("mon", NOW) == (at(day=7), True)

        # "next <weekday>" is a week on from that
        assert parse("next monday", NOW) == (at(day=14), True)
        assert parse("next friday", NOW) == (at(day=11), True)

        assert parse("fri 7pm", NOW) == (at(day=4, hour=19), True)

    def test_named_periods(self):
        assert parse("this weekend", NOW) == (at(day=5), True)
        assert parse("end of month", NOW) == (at(day=30), True)
        assert parse("someday", NOW) == (at(month=11), True)
        assert parse("mid january", NOW) == (at(year=2027, month=1, day=15), True)

    def test_day_first(self):
        assert parse("5.9", NOW) == (at(day=5), True)
        assert parse("05.09.2026", NOW) == (at(day=5), True)
        assert parse("1/2", NOW) == (at(month=2, day=1), True)

        # ISO is unambiguous and stays year-month-day
        assert parse("2026-09-05", NOW) == (at(day=5), True)

    def test_dotted_dates(self):
        # the German way of writing one, trailing dot and all
        assert parse("19.07.", NOW) == (at(month=7, day=19), True)
        assert parse("19.7.", NOW) == (at(month=7, day=19), True)
        assert parse("1.1.", NOW) == (at(month=1, day=1), True)
        assert parse("31.12.", NOW) == (at(month=12, day=31), True)

        # dateutil reads a dotted pair as a day in the *current* month, quietly
        # dropping the month it was given
        assert parse("19.07", NOW) == (at(month=7, day=19), True)
        assert parse("1.5", NOW) == (at(month=5, day=1), True)

        # with a year, two digits or four
        assert parse("19.07.26", NOW) == (at(month=7, day=19), True)
        assert parse("19.07.2026", NOW) == (at(month=7, day=19), True)
        assert parse("1.1.27", NOW) == (at(year=2027, month=1, day=1), True)

        # a bare day is a day of this month
        assert parse("19.", NOW) == (at(day=19), True)

        # month and year, no day
        assert parse("07.2026", NOW) == (at(month=7, day=1), True)

    def test_dotted_dates_with_times(self):
        assert parse("19.07. 16:00", NOW) == (at(month=7, day=19, hour=16), True)
        assert parse("19.07. at 16:00", NOW) == (at(month=7, day=19, hour=16), True)
        assert parse("19.7. 4pm", NOW) == (at(month=7, day=19, hour=16), True)
        assert parse("19.07.26 morning", NOW) == (at(month=7, day=19, hour=9), True)

    def test_impossible_dotted_dates(self):
        # a shape that looks like a dotted date but is not one is a typo, not
        # something to hand to dateutil for a guess
        for text in ("32.01.", "19.13.", "0.5.", "31.11.", "31.04.", "1..2",
                     "19.07.123", "1.2.3.4", "..", "0.0."):
            assert parse(text, NOW) == (None, False), text

        # 2026 is not a leap year, 2024 is
        assert parse("29.02.26", NOW) == (None, False)
        assert parse("29.02.24", NOW) == (datetime(2024, 2, 29), True)

    def test_other_separators(self):
        assert parse("19/07", NOW) == (at(month=7, day=19), True)
        assert parse("19/07/26", NOW) == (at(month=7, day=19), True)
        assert parse("19-07", NOW) == (at(month=7, day=19), True)
        assert parse("7/4", NOW) == (at(month=4, day=7), True)

    def test_clearing(self):
        assert parse("", NOW) == (None, True)
        assert parse("no date", NOW) == (None, True)
        assert parse("none", NOW) == (None, True)

    def test_unparseable(self):
        assert parse("?????", NOW) == (None, False)
        assert parse("asdfgh", NOW) == (None, False)
        assert parse("in 5 bananas", NOW) == (None, False)
