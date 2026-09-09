"""
Notes: the window on a todo's note, and the pinned scratchpad
"""

from unittest.mock import patch

from dooit.api import PinnedNote, Todo
from dooit.ui.screens.note import (
    MODE_INSERT,
    MODE_NORMAL,
    RULE,
    NoteScreen,
    NoteScreenBase,
)
from dooit.ui.screens.pinned_note import PinnedNoteScreen
from tests.test_ui.ui_base import (
    boot,
    commit_line,
    create_and_move_to_todo,
    run_pilot,
)


async def open_note(pilot, description: str = "task with a note") -> NoteScreen:
    """A project, a todo, and the note window opened on it with space"""

    await create_and_move_to_todo(pilot)
    await pilot.press("n")
    await commit_line(pilot, description)

    await pilot.press(" ")
    await pilot.pause()

    screen = pilot.app.screen
    assert isinstance(screen, NoteScreen)
    return screen


async def test_space_opens_the_note_window():
    async with run_pilot() as pilot:
        screen = await open_note(pilot, "the todo")

        # Titled by the todo, opened to be read
        assert screen.editor.border_title == "the todo"
        assert screen.editor.mode == MODE_NORMAL


async def test_writing_a_note_and_closing_saves_it():
    async with run_pilot() as pilot:
        app = pilot.app
        screen = await open_note(pilot)

        await pilot.press("i")
        assert screen.editor.mode == MODE_INSERT

        await pilot.press(*list("remember the milk"))
        await pilot.press("escape")  # back to NORMAL
        assert screen.editor.mode == MODE_NORMAL

        await pilot.press("escape")  # close the window
        await pilot.pause()

        assert not isinstance(app.screen, NoteScreenBase)
        assert Todo.all()[0].note == "remember the milk"


async def test_the_note_opens_on_what_it_holds():
    async with run_pilot() as pilot:
        screen = await open_note(pilot)

        await pilot.press("i")
        await pilot.press(*list("first draft"))
        await pilot.press("escape", "escape")
        await pilot.pause()

        # Open it again: the text is there, and typing continues it
        await pilot.press(" ")
        await pilot.pause()

        screen = pilot.app.screen
        assert isinstance(screen, NoteScreen)
        assert screen.editor.text == "first draft"

        await pilot.press("A")  # insert at the end of the line
        await pilot.press(*list(" and more"))
        await pilot.press("escape", "escape")
        await pilot.pause()

        assert Todo.all()[0].note == "first draft and more"


async def test_normal_mode_letters_do_not_write():
    async with run_pilot() as pilot:
        app = pilot.app
        await open_note(pilot)

        await pilot.press(*list("kjl"))  # motions, not letters
        await pilot.press("escape")
        await pilot.pause()

        assert not isinstance(app.screen, NoteScreenBase)
        assert Todo.all()[0].note == ""


async def test_clear_note_asks_first():
    async with run_pilot() as pilot:
        screen = await open_note(pilot)

        await pilot.press("i")
        await pilot.press(*list("precious words"))
        await pilot.press("escape")

        await pilot.press("ctrl+d")
        await pilot.pause()
        assert screen.awaiting_clear

        # Anything but y leaves the note exactly where it is
        await pilot.press("n")
        await pilot.pause()
        assert not screen.awaiting_clear
        assert screen.editor.text == "precious words"

        await pilot.press("ctrl+d")
        await pilot.press("y")
        await pilot.pause()

        assert screen.editor.text == ""

        await pilot.press("escape")
        await pilot.pause()
        assert Todo.all()[0].note == ""


async def test_note_marks_the_row():
    """The paper icon: a row with a note is told apart from one without"""

    async with run_pilot() as pilot:
        app = pilot.app
        await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "plain")

        formatter = app.api.formatter.todos.note
        todo = Todo.all()[0]

        assert formatter.format_value(todo.note, todo).plain.strip() == ""

        todo.note = "something"
        todo.save()

        assert formatter.format_value(todo.note, todo).plain.strip() != ""


async def test_bold_and_bullet_markup():
    async with run_pilot() as pilot:
        screen = await open_note(pilot)

        await pilot.press("i")
        await pilot.press(*list("word"))

        # Select the line and wrap it bold
        await pilot.press("ctrl+a", "ctrl+b")
        assert screen.editor.text == "**word**"

        # A bullet goes at the head of the line
        await pilot.press("ctrl+l")
        assert screen.editor.text == "• **word**"

        # And comes off it again
        await pilot.press("ctrl+l")
        assert screen.editor.text == "**word**"

        await pilot.press("escape", "escape")
        await pilot.pause()


async def test_header_draws_a_rule_under_the_line():
    async with run_pilot() as pilot:
        screen = await open_note(pilot)

        await pilot.press("i")
        await pilot.press(*list("Section"))
        await pilot.press("ctrl+t")
        await pilot.pause()

        lines = screen.editor.text.splitlines()
        assert lines[0] == "Section"
        assert set(lines[1]) == {RULE}

        # The same key takes the rule away again
        await pilot.press("ctrl+t")
        assert screen.editor.text == "Section"

        await pilot.press("escape", "escape")
        await pilot.pause()


async def test_open_link_inside_the_note():
    async with run_pilot() as pilot:
        opened = []

        with patch(
            "dooit.ui.screens.note.open_url",
            lambda url: opened.append(url) or True,
        ):
            await open_note(pilot)

            await pilot.press("i")
            await pilot.press(*list("see https://example.com here"))
            await pilot.press("escape")

            # The cursor sits at the end, past the link: no link under it
            await pilot.press("o")
            await pilot.pause()
            assert opened == []

            # Walk back onto the link and open it
            await pilot.press("b", "b")  # word left, onto the url
            await pilot.press("o")
            await pilot.pause()

            assert opened == ["https://example.com"]

        await pilot.press("escape")
        await pilot.pause()


async def test_pinned_note_via_m():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await pilot.press("m")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, PinnedNoteScreen)
        assert screen.editor.border_title == "Pinned Note"

        await pilot.press("i")
        await pilot.press(*list("a thought with no task yet"))
        await pilot.press("escape", "escape")
        await pilot.pause()

        assert not isinstance(app.screen, NoteScreenBase)
        assert PinnedNote.get_text() == "a thought with no task yet"

        # It is one note for the whole app: opening it again shows the same
        await pilot.press("m")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, PinnedNoteScreen)
        assert screen.editor.text == "a thought with no task yet"

        await pilot.press("escape")
        await pilot.pause()
