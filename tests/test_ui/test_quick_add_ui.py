"""
The quick add overlay: a whole task typed in one line over the app
"""

from datetime import date, timedelta

from dooit.api import Project, Todo
from dooit.ui.screens.quick_add import QuickAddScreen
from tests.test_ui.ui_base import (
    boot,
    new_project,
    notification_message,
    run_pilot,
)


async def open_quick_add(pilot) -> QuickAddScreen:
    await pilot.press("C")
    await pilot.pause()

    screen = pilot.app.screen
    assert isinstance(screen, QuickAddScreen)
    return screen


async def test_quick_add_into_the_open_project():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        await new_project(pilot, "inbox")

        await open_quick_add(pilot)
        await pilot.press(*list("call the dentist p1 tomorrow"))
        await pilot.press("enter")
        await pilot.pause()

        assert not isinstance(app.screen, QuickAddScreen)

        (todo,) = Todo.all()
        assert todo.description == "call the dentist"
        assert todo.priority == 1
        assert todo.scheduled is not None
        assert todo.scheduled.date() == date.today() + timedelta(days=1)
        assert todo.parent_project is not None
        assert todo.parent_project.description == "inbox"

        message = notification_message(app)
        assert message is not None and "call the dentist" in message


async def test_quick_add_names_another_project():
    async with run_pilot() as pilot:
        await boot(pilot)
        await new_project(pilot, "inbox")
        await new_project(pilot, "work")

        # The panes sit on "work"; the line files it under "inbox"
        await open_quick_add(pilot)
        await pilot.press(*list("file taxes #inbox @paper"))
        await pilot.press("enter")
        await pilot.pause()

        (todo,) = Todo.all()
        assert todo.parent_project.description == "inbox"
        # The label rides along in the description, as a tag
        assert todo.description == "file taxes @paper"
        assert todo.tags == ["@paper"]


async def test_quick_add_asks_before_building_a_project():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        await new_project(pilot, "inbox")

        await open_quick_add(pilot)
        await pilot.press(*list("buy nails #diy"))
        await pilot.press("enter")
        await pilot.pause()

        # The overlay stays up, holding the question
        assert isinstance(app.screen, QuickAddScreen)

        await pilot.press("y")
        await pilot.pause()

        assert not isinstance(app.screen, QuickAddScreen)

        diy = next(p for p in Project.all() if p.description == "diy")
        (todo,) = Todo.all()
        assert todo.parent_project == diy


async def test_quick_add_create_declined():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        await new_project(pilot, "inbox")

        await open_quick_add(pilot)
        await pilot.press(*list("buy nails #diy"))
        await pilot.press("enter")
        await pilot.pause()

        await pilot.press("n")
        await pilot.pause()

        # The question is settled, the line still there to be edited
        assert isinstance(app.screen, QuickAddScreen)
        assert Todo.all() == []
        assert [p.description for p in Project.all()] == ["inbox"]

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, QuickAddScreen)


async def test_quick_add_without_a_project_needs_one_named():
    """From a fixed project there is no pane to fall back to"""

    async with run_pilot() as pilot:
        app = await boot(pilot)

        # Straight from the Today pane, naming no project
        await open_quick_add(pilot)
        await pilot.press(*list("homeless task"))
        await pilot.press("enter")
        await pilot.pause()

        # Refused with a warning drawn into the overlay, which stays up
        assert isinstance(app.screen, QuickAddScreen)
        assert Todo.all() == []

        await pilot.press("escape")
        await pilot.pause()


async def test_quick_add_escape_cancels():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        await new_project(pilot, "inbox")

        await open_quick_add(pilot)
        await pilot.press(*list("half a thought"))
        await pilot.press("escape")
        await pilot.pause()

        assert not isinstance(app.screen, QuickAddScreen)
        assert Todo.all() == []


async def test_quick_add_rejects_an_unreadable_line():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        await new_project(pilot, "inbox")

        screen = await open_quick_add(pilot)
        await pilot.press(*list("#inbox p1"))  # no description at all
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, QuickAddScreen)
        assert screen._warning != ""
        assert Todo.all() == []

        await pilot.press("escape")
        await pilot.pause()


async def test_quick_add_app_keys_are_letters_here():
    """`q` toggles shading in the app; in the line it is just a letter"""

    async with run_pilot() as pilot:
        app = await boot(pilot)
        await new_project(pilot, "inbox")

        shading = app.api.vars.row_shading

        await open_quick_add(pilot)
        await pilot.press(*list("quiet quality quest"))
        await pilot.press("enter")
        await pilot.pause()

        (todo,) = Todo.all()
        assert todo.description == "quiet quality quest"
        assert app.api.vars.row_shading == shading
