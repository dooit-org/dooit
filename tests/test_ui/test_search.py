from datetime import datetime

from textual.pilot import Pilot
from textual.widgets import ContentSwitcher

from dooit.api import COMPLETED, Project, Todo
from dooit.ui.screens.search import BINNED, DONE, MAX_ROWS, SearchScreen
from dooit.ui.tui import Dooit
from dooit.ui.widgets.trees.todos_tree import TodosTree
from tests.test_ui.ui_base import run_pilot

ITEMS = ["apple", "apps", "applet", "apricot"]


async def seed(pilot: Pilot) -> Project:
    """
    Fills the database with a project of tasks and shows the panes it

    Written straight to the database rather than typed into the panes: what is
    being tested is finding a task that is somewhere else entirely, and typing
    one in leaves the cursor sitting on it.
    """

    app = pilot.app
    assert isinstance(app, Dooit)

    # Filed under the root the pane itself was built with, rather than under
    # one looked up again: the pane draws what hangs off the object it holds
    project = app.api.vars.projects_tree.model.add_project()
    project.description = "project"
    project.save()

    for item in ITEMS:
        todo = project.add_todo()
        todo.description = item
        todo.save()

    app.api.vars.projects_tree.force_refresh()
    await pilot.pause()

    return project


def visible_todos(app: Dooit) -> TodosTree:
    tree = app.screen.query_one(
        "#todo_switcher", expect_type=ContentSwitcher
    ).visible_content

    assert isinstance(tree, TodosTree)
    return tree


async def open_search(pilot: Pilot) -> SearchScreen:
    await pilot.press("/")
    await pilot.pause()

    screen = pilot.app.screen
    assert isinstance(screen, SearchScreen)

    return screen


async def test_search_narrows_and_orders():
    async with run_pilot() as pilot:
        await seed(pilot)
        screen = await open_search(pilot)

        # Nothing typed yet, so there is nothing to offer
        assert screen._matches == []

        await pilot.press(*list("app"))
        await pilot.pause()

        # Every task starting with what was typed, in alphabetical order:
        # none of them carries a deadline to be told apart by
        assert [match.todo.description for match in screen._matches] == [
            "apple",
            "applet",
            "apps",
        ]

        # A word none of the tasks says, but the project they are in does
        await pilot.press(*(["backspace"] * 3))
        await pilot.press(*list("project"))
        await pilot.pause()

        assert len(screen._matches) == len(ITEMS)

        # And one nobody says at all
        await pilot.press(*list("zzz"))
        await pilot.pause()

        assert screen._matches == []


async def test_search_jumps_to_the_task():
    async with run_pilot() as pilot:
        await seed(pilot)
        await open_search(pilot)

        await pilot.press(*list("app"))
        await pilot.press("down")
        await pilot.pause()

        await pilot.press("enter")
        await pilot.pause()
        await pilot.pause()

        app = pilot.app
        assert isinstance(app, Dooit)
        assert not isinstance(app.screen, SearchScreen)

        todos = visible_todos(app)
        assert todos.current_model.description == "applet"
        assert app.focused is todos


async def test_search_puts_finished_and_binned_last():
    async with run_pilot() as pilot:
        await seed(pilot)

        binned, completed = Todo.all()[0], Todo.all()[1]
        binned.binned_at = datetime.now()
        binned.save()
        completed.toggle_complete()
        completed.save()

        screen = await open_search(pilot)
        await pilot.press(*list("app"))
        await pilot.pause()

        # Everything is still findable; what changes is the block it is in,
        # and the blocks come in one order
        sections = [match.section for match in screen._matches]
        assert sections == sorted(sections)
        assert sections[-2:] == [DONE, BINNED]

        found = {match.todo.description: match.section for match in screen._matches}
        assert found[completed.description] == DONE
        assert found[binned.description] == BINNED


async def test_search_jumps_to_the_pane_a_finished_task_moved_to():
    async with run_pilot() as pilot:
        await seed(pilot)

        completed = Todo.all()[0]
        completed.description = "singular finished thing"
        completed.toggle_complete()
        completed.save()

        await open_search(pilot)
        await pilot.press(*list("singular"))
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.pause()

        app = pilot.app
        assert isinstance(app, Dooit)

        todos = visible_todos(app)
        assert todos.model is COMPLETED
        assert todos.current_model.description == completed.description


async def test_search_scrolls_through_the_matches():
    async with run_pilot() as pilot:
        project = await seed(pilot)

        for index in range(MAX_ROWS + 5):
            todo = project.add_todo()
            todo.description = f"apple number {index}"
            todo.save()

        screen = await open_search(pilot)
        await pilot.press(*list("apple"))
        await pilot.pause()

        assert len(screen._matches) > MAX_ROWS
        assert screen._offset == 0

        # The window stays put until the cursor walks off the end of it
        for _ in range(MAX_ROWS - 1):
            await pilot.press("down")

        await pilot.pause()
        assert screen._offset == 0

        await pilot.press("down")
        await pilot.pause()
        assert screen._offset == 1

        # Back up to the top, taking the window with it
        for _ in range(MAX_ROWS):
            await pilot.press("up")

        await pilot.pause()
        assert (screen._index, screen._offset) == (0, 0)

        # And round the end of the list in one key
        await pilot.press("up")
        await pilot.pause()
        assert screen._index == len(screen._matches) - 1
        assert screen._offset == len(screen._matches) - MAX_ROWS


async def test_search_can_be_cancelled():
    async with run_pilot() as pilot:
        await seed(pilot)
        await open_search(pilot)

        await pilot.press("escape")
        await pilot.pause()

        assert not isinstance(pilot.app.screen, SearchScreen)
