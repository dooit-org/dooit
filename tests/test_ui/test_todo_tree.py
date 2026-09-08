"""
The tasks pane of a stored project: adding, editing, and every column
"""

from datetime import date, datetime, timedelta

from pytest import raises

from dooit.api import Todo
from dooit.api.exceptions import NoNodeError
from dooit.ui.api.widgets import TodoWidget
from dooit.ui.tui import Dooit
from dooit.ui.widgets.renderers.base_renderer import BaseRenderer
from tests.test_ui.ui_base import (
    commit_line,
    create_and_move_to_todo,
    highlighted_index,
    notification_message,
    run_pilot,
    tree_options,
)


def custom_formatter(value, todo):
    return "??"


async def test_todo_tree_focus():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        await create_and_move_to_todo(pilot)


async def test_no_node_error():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        with raises(NoNodeError):
            tree.current


async def test_add_todo_via_keys():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "first")

        await pilot.press("n")
        await commit_line(pilot, "second")

        assert [t.description for t in Todo.all()] == ["first", "second"]
        assert len(tree_options(tree)) == 2
        assert highlighted_index(tree) == 1


async def test_escape_discards_a_new_todo():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await pilot.press(*list("never kept"))
        await pilot.press("escape")
        await pilot.pause()

        assert Todo.all() == []
        assert tree_options(tree) == []


async def test_blank_todo_is_dropped():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "   ")

        assert Todo.all() == []
        assert tree_options(tree) == []


async def test_blanking_a_todo_with_steps_asks_first():
    """Dropping it would take everything under it along"""

    async with run_pilot() as pilot:
        app = pilot.app
        await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "parent")
        await pilot.press("N")
        await commit_line(pilot, "step")

        # Blank the parent's name and commit
        await pilot.press("k")  # up to the parent
        await pilot.press("i", "ctrl+l")
        await pilot.press("enter")
        await pilot.pause()

        assert app.bar_switcher.current == "confirm_bar"

        await pilot.press("n")
        await pilot.pause()

        # Cancelled: both rows survive, the parent just has no name yet
        assert len(Todo.all()) == 2


async def test_add_child_and_expansion():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "task")
        await pilot.press("N")
        await commit_line(pilot, "step")

        step = next(t for t in Todo.all() if t.description == "step")
        assert step.parent_todo is not None
        assert step.parent_todo.description == "task"

        # The parent was expanded on the way in; the cursor is on the step
        assert len(tree_options(tree)) == 2
        assert tree.current_model.uuid == step.uuid

        # Fold the parent away and open it again
        await pilot.press("k", "h")
        await pilot.pause()
        assert len(tree_options(tree)) == 1

        await pilot.press("h")
        await pilot.pause()
        assert len(tree_options(tree)) == 2


async def test_edit_description():
    async with run_pilot() as pilot:
        await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "old")

        await pilot.press("i", "ctrl+l")
        await commit_line(pilot, "new")

        assert Todo.all()[0].description == "new"


async def test_todo_formatter():
    def get_formatted(renderer: BaseRenderer, attr: str):
        component = renderer._get_component(attr)
        formatter = renderer.tree.formatter
        return (
            getattr(formatter, attr)
            .format_value(component.model_value, component.model)
            .markup
        )

    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        renderer = tree.current
        assert get_formatted(renderer, "description") == "nixos"

        app.api.formatter.todos.description.add(custom_formatter)
        assert get_formatted(renderer, "description") == "??"


async def test_todo_tree_layout():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        table = tree.current.make_renderable()
        assert table.columns[0].header == "status"

        app.api.layouts.todo_layout = [TodoWidget.description]
        table = tree.current.make_renderable()
        assert table.columns[0].header == "description"


async def test_incorrect_edit():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        assert not tree.current.start_edit("incorrect")


async def test_remove_todo():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        # `yy` is the delete that asks first
        await pilot.press("y", "y")
        await pilot.pause()

        assert len(tree_options(tree)) == 1
        assert highlighted_index(tree) == 0
        assert tree.current_model.description == "nixos"

        await pilot.press("y")
        await pilot.pause()

        assert len(tree_options(tree)) == 0
        assert tree.highlighted is None
        assert Todo.all() == []


async def test_due():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        await pilot.press("d")
        await commit_line(pilot, "2022-01-01")

        todo = tree.current_model
        assert isinstance(todo, Todo)
        assert todo.due == datetime(2022, 1, 1)


async def test_scheduled():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        await pilot.press("s")
        await commit_line(pilot, "2033-05-05")

        todo = tree.current_model
        assert isinstance(todo, Todo)
        assert todo.scheduled == datetime(2033, 5, 5)
        assert todo.due is None


async def test_due_natural_language():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        await pilot.press("d")
        await commit_line(pilot, "tom 16:00")

        todo = tree.current_model
        assert isinstance(todo, Todo)

        expected = datetime.now().replace(
            hour=16, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        assert todo.due == expected


async def test_due_preview_while_editing():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        await pilot.press("d")
        await pilot.press(*list("tom"))

        component = tree.current._get_component("due")
        preview = component.render_editing(tree.current.theme).plain

        tomorrow = datetime.now() + timedelta(days=1)
        assert preview.endswith(f"→ {tomorrow.strftime('%d.%m.%Y')}")

        # and an expression that means nothing says so, rather than guessing
        await pilot.press("ctrl+l")
        await pilot.press(*list("asdfgh"))
        assert component.render_editing(tree.current.theme).plain.endswith("→ ?")

        await pilot.press("escape")


async def test_due_invalid_keeps_previous_value():
    async with run_pilot() as pilot:
        app = pilot.app
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        await pilot.press("d")
        await commit_line(pilot, "2022-01-01")

        todo = tree.current_model
        assert isinstance(todo, Todo)
        assert todo.due == datetime(2022, 1, 1)

        # Committing garbage: the date that was there survives, and the bar
        # says why instead of the edit being silently dropped
        await pilot.press("d", "ctrl+l")
        await commit_line(pilot, "asdfgh")

        assert todo.due == datetime(2022, 1, 1)
        assert not tree.is_editing

        message = notification_message(app)
        assert message is not None and "asdfgh" in message


async def test_due_refused_on_recurring_todo():
    """What repeats is never owed by a date, and typing one is turned away"""

    async with run_pilot() as pilot:
        app = pilot.app
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "weekly review")

        await pilot.press("r")
        await commit_line(pilot, "1w")

        todo = tree.current_model
        assert isinstance(todo, Todo)
        assert todo.recurrence == timedelta(weeks=1)

        await pilot.press("d")
        await commit_line(pilot, "tomorrow")

        assert todo.due is None
        message = notification_message(app)
        assert message is not None and "recurring" in message


async def test_priority_keybinds():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        todo = tree.current_model
        assert isinstance(todo, Todo)
        assert todo.priority == 0

        await pilot.press("p", "1")
        await pilot.pause()
        assert todo.priority == 1

        await pilot.press("p", "3")
        await pilot.pause()
        assert todo.priority == 3

        await pilot.press("p", "0")
        await pilot.pause()
        assert todo.priority == 0


async def test_effort_keybinds():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        todo = tree.current_model
        assert isinstance(todo, Todo)
        assert todo.effort == 0

        await pilot.press("e", "2")
        await pilot.pause()
        assert todo.effort == 2

        await pilot.press("e", "0")
        await pilot.pause()
        assert todo.effort == 0


async def test_status_change():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        await pilot.press("d")
        await commit_line(pilot, "2022-01-01")

        todo = tree.current_model
        assert isinstance(todo, Todo)
        assert todo.status == "overdue"

        todo.toggle_complete()
        assert todo.status == "completed"


async def test_effort_editing_needs_the_column():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        todo = tree.current_model
        assert isinstance(todo, Todo)

        app.api.layouts.todo_layout = [TodoWidget.description]
        assert not tree.start_edit("effort")  # column is not in the layout

        app.api.layouts.todo_layout = [
            TodoWidget.description,
            TodoWidget.effort,
        ]
        tree.start_edit("effort")
        await pilot.press("2")
        await pilot.press("enter")
        await pilot.pause()

        assert todo.effort == 2


async def test_recurrence_change():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "nixos")

        todo = tree.current_model
        assert isinstance(todo, Todo)
        assert todo.recurrence is None

        await pilot.press("r")
        await commit_line(pilot, "1d")

        assert todo.recurrence == timedelta(days=1)


async def test_completing_a_recurring_todo_bounces_it():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "daily standup")

        await pilot.press("s")
        await commit_line(pilot, "today")
        await pilot.press("r")
        await commit_line(pilot, "1d")

        todo = tree.current_model
        assert isinstance(todo, Todo)

        await pilot.press("c")
        await pilot.pause()

        # Never finished, only done for now: pending again, one day on, and
        # still the only row of its pane
        assert todo.is_pending
        assert todo.scheduled is not None
        assert todo.scheduled.date() == date.today() + timedelta(days=1)
        assert len(tree_options(tree)) == 1
