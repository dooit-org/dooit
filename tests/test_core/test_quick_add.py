"""
The quick add line: a whole task read out of one typed sentence
"""

from datetime import datetime

from pytest import raises

from dooit.utils.quick_add import QuickAddError, parse_quick_add, split_path

# A Wednesday morning, so relative dates resolve the same way every run
NOW = datetime(2026, 9, 2, 10, 30)


def test_a_bare_line_is_all_description():
    spec = parse_quick_add("call the dentist", NOW)

    assert spec.description == "call the dentist"
    assert spec.project == ""
    assert spec.labels == []
    assert spec.priority == 0
    assert spec.effort == 0
    assert spec.scheduled is None
    assert spec.due is None


def test_the_whole_sentence_at_once():
    spec = parse_quick_add("call the dentist #Home @phone p1 e2 tomorrow", NOW)

    assert spec.description == "call the dentist"
    assert spec.project == "Home"
    assert spec.labels == ["phone"]
    assert spec.priority == 1
    assert spec.effort == 2
    assert spec.scheduled == datetime(2026, 9, 3)


def test_project_marker():
    assert parse_quick_add("x #Home", NOW).project == "Home"

    # Quoted, so a project name can have a space in it
    assert parse_quick_add('x #"My House"', NOW).project == "My House"

    # A path picks a nested project
    assert parse_quick_add("x #Home/Garden", NOW).project == "Home/Garden"


def test_only_one_project():
    with raises(QuickAddError):
        parse_quick_add("x #a #b", NOW)


def test_labels_are_stored_as_tags():
    spec = parse_quick_add("call mum @family @phone", NOW)

    assert spec.labels == ["family", "phone"]
    assert spec.described == "call mum @family @phone"


def test_duplicate_labels_collapse():
    spec = parse_quick_add("x @a @a", NOW)
    assert spec.labels == ["a"]


def test_an_at_inside_a_word_is_not_a_label():
    spec = parse_quick_add("mail bob@example.com", NOW)

    assert spec.labels == []
    assert spec.description == "mail bob@example.com"


def test_a_label_must_be_one_word():
    with raises(QuickAddError):
        parse_quick_add('x @"two words"', NOW)


def test_a_bare_marker_is_an_error():
    with raises(QuickAddError):
        parse_quick_add("buy milk #", NOW)

    with raises(QuickAddError):
        parse_quick_add("buy milk @", NOW)


def test_scales():
    spec = parse_quick_add("x p2 e3", NOW)
    assert spec.priority == 2
    assert spec.effort == 3


def test_scales_out_of_range():
    with raises(QuickAddError):
        parse_quick_add("x p4", NOW)

    with raises(QuickAddError):
        parse_quick_add("x e9", NOW)


def test_bare_date_is_the_scheduled_day():
    spec = parse_quick_add("water plants tomorrow", NOW)

    assert spec.description == "water plants"
    assert spec.scheduled == datetime(2026, 9, 3)
    assert spec.due is None
    assert spec.date_text == "tomorrow"


def test_date_with_time():
    spec = parse_quick_add("standup tomorrow 09:00", NOW)
    assert spec.scheduled == datetime(2026, 9, 3, 9, 0)


def test_multi_word_date_is_read_whole():
    spec = parse_quick_add("review next monday at 16:00", NOW)

    assert spec.description == "review"
    assert spec.scheduled == datetime(2026, 9, 14, 16, 0)


def test_lead_word_goes_with_the_date():
    spec = parse_quick_add("call mum on friday", NOW)

    assert spec.description == "call mum"
    assert spec.scheduled == datetime(2026, 9, 4)


def test_the_last_date_in_the_line_wins():
    """Anything earlier that merely looks like one is part of the name"""

    spec = parse_quick_add("friday standup notes tomorrow", NOW)

    assert spec.description == "friday standup notes"
    assert spec.scheduled == datetime(2026, 9, 3)


def test_a_joining_word_keeps_two_halves_apart():
    spec = parse_quick_add("buy milk tomorrow and eggs", NOW)

    assert spec.scheduled == datetime(2026, 9, 3)
    assert spec.description == "buy milk and eggs"


def test_numbers_are_not_days():
    spec = parse_quick_add("buy 5 apples", NOW)

    assert spec.scheduled is None
    assert spec.description == "buy 5 apples"


def test_due_is_asked_for_by_name():
    spec = parse_quick_add("thesis due=friday", NOW)

    assert spec.description == "thesis"
    assert spec.due == datetime(2026, 9, 4)
    assert spec.scheduled is None


def test_due_expression_runs_past_the_word():
    spec = parse_quick_add("thesis due=next monday at 16:00", NOW)

    assert spec.due == datetime(2026, 9, 14, 16, 0)
    assert spec.description == "thesis"


def test_due_stops_at_a_field_of_its_own():
    spec = parse_quick_add("thesis due=fri p1", NOW)

    assert spec.due == datetime(2026, 9, 4)
    assert spec.priority == 1


def test_due_and_scheduled_together():
    spec = parse_quick_add("thesis tomorrow due=3w", NOW)

    assert spec.scheduled == datetime(2026, 9, 3)
    assert spec.due == datetime(2026, 9, 23)


def test_unreadable_due_is_an_error():
    """It was asked for by name, so filing it quietly would be losing it"""

    with raises(QuickAddError):
        parse_quick_add("thesis due=banana", NOW)

    with raises(QuickAddError):
        parse_quick_add("thesis due=", NOW)


def test_two_deadlines_are_an_error():
    with raises(QuickAddError):
        parse_quick_add("thesis due=fri due=mon", NOW)


def test_a_task_needs_a_description():
    with raises(QuickAddError):
        parse_quick_add("#Home p1 tomorrow", NOW)

    with raises(QuickAddError):
        parse_quick_add("", NOW)


def test_described_appends_the_labels():
    spec = parse_quick_add("call mum @family", NOW)
    assert spec.described == "call mum @family"

    spec = parse_quick_add("call mum", NOW)
    assert spec.described == "call mum"


def test_split_path():
    assert split_path("Home") == ("Home",)
    assert split_path("Home/Garden") == ("Home", "Garden")
    assert split_path(" Home / Garden ") == ("Home", "Garden")
    assert split_path("//") == ()
