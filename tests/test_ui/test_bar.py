"""
The bar under the panes: the status line, and the bars that take it over

Notifications, the y/N that guards a delete, and the field editor a fixed
pane borrows when a hidden column is edited. (The old modal sort bar has no
key bound to it any more; the sort chords are tested in test_sort.py.)
"""

from dooit.api import Todo
from dooit.ui.widgets.bars import StatusBar
from tests.test_ui.ui_base import (
    boot,
    create_and_move_to_todo,
    new_project,
    new_todo,
    notification_message,
    run_pilot,
)


async def test_the_status_bar_is_the_default():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        assert app.bar_switcher.current == "status_bar"
        assert isinstance(app.bar_switcher.visible_content, StatusBar)
        assert not app.bar_switcher.is_focused


async def test_notifications_show_in_the_bar():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        app.api.notify("hello from the test", "info")
        await pilot.pause()

        assert app.bar_switcher.current == "notification_bar"
        assert notification_message(app) == "hello from the test"

        # An info notification does not take the keyboard
        assert not app.bar_switcher.is_focused


async def test_confirm_bar_takes_the_keyboard_and_answers_no():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        await new_project(pilot, "project")
        todo = await new_todo(pilot, "precious")

        # `yy` deletes for good, and that is the one edit that asks first
        await pilot.press("y", "y")
        await pilot.pause()

        assert app.bar_switcher.current == "confirm_bar"
        assert app.bar_switcher.is_focused

        # While the question stands, other keys are answers, not commands
        await pilot.press("n")
        await pilot.pause()

        assert todo in Todo.all()
        assert notification_message(app) == "The items were retained"


async def test_confirm_bar_answers_yes():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        await new_project(pilot, "project")
        await new_todo(pilot, "doomed")

        await pilot.press("y", "y")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()

        assert Todo.all() == []
        assert notification_message(app) == "The items were deleted"


async def test_field_bar_edits_a_hidden_column():
    """
    Editing the scheduled date from Today: the column is not drawn there,
    so the buffer goes to the bar instead of a column the pane does not have
    """

    async with run_pilot() as pilot:
        app = await boot(pilot)
        await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await pilot.press(*list("planned work"))
        await pilot.press("enter")
        await pilot.pause()

        # Schedule it for today so the Today pane picks it up
        await pilot.press("s")
        await pilot.press(*list("today"))
        await pilot.press("enter")
        await pilot.pause()

        await pilot.press("g", "t")
        await pilot.pause()

        # An edit of the hidden column moves the buffer into the bar
        await pilot.press("s")
        await pilot.pause()

        assert app.bar_switcher.current == "field_bar"

        await pilot.press("ctrl+l")  # clear the buffer
        await pilot.press(*list("tomorrow"))
        await pilot.press("enter")
        await pilot.pause()

        from datetime import date, timedelta

        todo = Todo.all()[0]
        assert todo.scheduled is not None
        assert todo.scheduled.date() == date.today() + timedelta(days=1)
