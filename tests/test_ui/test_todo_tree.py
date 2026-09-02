from datetime import datetime, timedelta
from pytest import raises
from dooit.api.exceptions import NoNodeError
from dooit.api import Todo
from dooit.ui.api.widgets import TodoWidget
from dooit.ui.widgets.renderers.base_renderer import BaseRenderer
from tests.test_ui.ui_base import (
    run_pilot,
    create_and_move_to_todo,
    tree_options,
    highlighted_index,
)
from dooit.ui.tui import Dooit


def custom_formatter(value, todo):
    return "??"


async def test_todo_tree_focus():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        await create_and_move_to_todo(pilot)


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

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        renderer = tree.current
        assert get_formatted(renderer, "description") == "nixos"

        app.api.formatter.todos.description.add(custom_formatter)
        assert get_formatted(renderer, "description") == "??"


async def test_no_node_error():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        with raises(NoNodeError):
            tree.current


async def test_todo_tree_layout():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        table = tree.current.make_renderable()
        assert table.columns[0].header == "status"

        app.api.layouts.todo_layout = [TodoWidget.description]
        table = tree.current.make_renderable()
        assert table.columns[0].header == "description"


async def test_incorrect_edit():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        assert not tree.current.start_edit("incorrect")


async def test_remove_todo():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        tree.remove_node()
        await pilot.pause()

        assert len(tree_options(tree)) == 1
        assert highlighted_index(tree) == 0
        assert tree.current_model.description == "nixos"

        await pilot.press("y")
        assert len(tree_options(tree)) == 0
        assert tree.highlighted is None


async def test_due():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        app.api.edit_due()
        await pilot.press(*list("2022-01-01"))
        await pilot.press("escape")

        todo = tree.current_model
        assert isinstance(todo, Todo)

        assert todo.due == datetime(2022, 1, 1)


async def test_due_natural_language():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        app.api.edit_due()
        await pilot.press(*list("tom 16:00"))
        await pilot.press("escape")

        todo = tree.current_model
        assert isinstance(todo, Todo)

        expected = datetime.now().replace(
            hour=16, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        assert todo.due == expected


async def test_due_preview_while_editing():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        app.api.edit_due()
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
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        app.api.edit_due()
        await pilot.press(*list("2022-01-01"))
        await pilot.press("escape")

        todo = tree.current_model
        assert isinstance(todo, Todo)
        assert todo.due == datetime(2022, 1, 1)

        app.api.edit_due()
        await pilot.press(*list("asdfgh"))
        await pilot.press("escape")

        # the garbage is dropped and the date that was there survives
        assert todo.due == datetime(2022, 1, 1)

        # and the tree is genuinely out of the edit, not still eating keystrokes
        assert not tree.is_editing


async def test_priority():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        todo = tree.current_model
        assert isinstance(todo, Todo)

        assert todo.priority == 0

        tree.set_priority(1)
        await pilot.pause()
        assert todo.priority == 1

        tree.set_priority(0)
        await pilot.pause()
        assert todo.priority == 0


async def test_status_change():
    async with run_pilot() as pilot:
        await pilot.pause()
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        app.api.edit_due()
        await pilot.press(*list("2022-01-01"))
        await pilot.press("escape")

        todo = tree.current_model
        assert isinstance(todo, Todo)

        assert todo.status == "overdue"
        tree.toggle_complete()
        await pilot.pause()

        assert todo.status == "completed"


async def test_effort_change():
    async with run_pilot() as pilot:
        await pilot.pause()
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        todo = tree.current_model
        assert isinstance(todo, Todo)

        assert todo.effort == 0

        app.api.layouts.todo_layout = [TodoWidget.description]
        assert not tree.start_edit("effort")  # column is not in the layout

        app.api.layouts.todo_layout = [
            TodoWidget.effort
        ]  # make sure the column is there
        tree.start_edit("effort")
        await pilot.press("2")
        await pilot.press("escape")

        assert todo.effort == 2


async def test_recurrence_change():
    async with run_pilot() as pilot:
        await pilot.pause()
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        todo = tree.current_model
        assert isinstance(todo, Todo)

        assert todo.recurrence is None

        app.api.layouts.todo_layout = [
            TodoWidget.recurrence
        ]  # make sure the column is there
        tree.start_edit("recurrence")
        await pilot.press("1", "d")
        await pilot.press("escape")

        assert todo.recurrence == timedelta(days=1)
