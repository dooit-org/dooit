"""
The pinned note: one scratchpad for the whole of dooit
"""

from dooit.api import PinnedNote
from dooit.api.pinned_note import PINNED_NOTE_ID
from tests.test_core.core_base import *  # noqa


def test_the_note_starts_empty(session):
    assert PinnedNote.get_text() == ""


def test_the_note_is_one_row(session):
    first = PinnedNote.instance()
    second = PinnedNote.instance()

    assert first.id == second.id == PINNED_NOTE_ID
    assert len(session.query(PinnedNote).all()) == 1


def test_set_and_read_back(session):
    PinnedNote.set_text("remember the milk")
    assert PinnedNote.get_text() == "remember the milk"

    PinnedNote.set_text("something else")
    assert PinnedNote.get_text() == "something else"


def test_writing_the_same_text_is_a_no_op(session):
    """The editor saves on a debounce, so the same text arrives repeatedly"""

    PinnedNote.set_text("scratch")
    row = PinnedNote.instance()

    # A second identical write must not dirty the session (the db poller
    # would read it as a change made elsewhere and refresh every pane)
    PinnedNote.set_text("scratch")
    assert row not in session.dirty

    assert PinnedNote.get_text() == "scratch"
