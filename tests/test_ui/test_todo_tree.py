from datetime import datetime, timedelta

from pytest import raises

from dooit.models import Todo
from dooit.models.exceptions import NoNodeError
from dooit.ui.tui import Dooit
from dooit.ui.widgets.renderers.base_renderer import BaseRenderer
from tests.test_ui.ui_base import create_and_move_to_todo, run_pilot


def custom_formatter(todo):
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
        return getattr(formatter, attr).format_value(component.model).markup

    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        renderer = tree.current
        assert get_formatted(renderer, "description") == "nixos"

        app.api.formatter.todos.description.set(custom_formatter)
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

        app.api.layouts.todo_layout = ["description"]
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

        assert len(tree._options) == 1
        assert tree.highlighted == 0
        assert tree.current_model.description == "nixos"

        await pilot.press("y")
        assert len(tree._options) == 0
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


async def test_urgency():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        todo = tree.current_model
        assert isinstance(todo, Todo)

        urgency = todo.urgency
        tree.increase_urgency()

        await pilot.pause()
        assert todo.urgency == urgency + 1

        tree.decrease_urgency()
        await pilot.pause()
        assert todo.urgency == urgency


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
        assert not tree.start_edit("effort")

        app.api.layouts.todo_layout = ["effort"]  # make sure the column is there
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

        app.api.layouts.todo_layout = ["recurrence"]  # make sure the column is there
        tree.start_edit("recurrence")
        await pilot.press("1", "d")
        await pilot.press("escape")

        assert todo.recurrence == timedelta(days=1)
