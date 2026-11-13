from datetime import datetime, timedelta
from pytest import raises
from dooit.api.exceptions import NoNodeError
from dooit.api import Todo
from dooit.ui.api.widgets import TodoWidget
from dooit.ui.widgets.renderers.base_renderer import BaseRenderer
from tests.test_ui.ui_base import run_pilot, create_and_move_to_todo
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
        assert table.columns[0].header == "expand_indicator"
        assert table.columns[1].header == "status"

        app.api.layouts.todo_layout = [TodoWidget.description]
        table = tree.current.make_renderable()
        assert table.columns[1].header == "description"


async def test_expand_indicator():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("parent"))
        await pilot.press("escape")
        parent = tree.current_model

        def indicator() -> str:
            table = tree._renderers[parent.uuid].make_renderable()
            return list(table.columns[0].cells)[0]

        assert indicator() == ""

        tree.add_child_node()
        await pilot.press(*list("child"))
        await pilot.press("escape")
        assert indicator() == ""

        tree.toggle_expand_parent()
        assert indicator() == "+"

        tree.toggle_expand()
        assert indicator() == ""


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
        assert TodoWidget.effort in app.api.layouts.todo_layout

        await pilot.press("e")
        assert app.get_dooit_mode() == "INSERT"

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


async def test_recurring_completion_shows_new_child():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("rent"))
        await pilot.press("escape")
        parent_id = tree.current_model.uuid

        await pilot.press("r", "1", "w", "enter")
        await pilot.press("c")
        assert len(tree._options) == 1  # collapsed

        await pilot.press("z")
        assert len(tree._options) == 2

        await pilot.press("c")
        assert len(tree._options) == 3
        assert tree.node.id == parent_id


async def test_recurrence_in_default_layout():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("nixos"))
        await pilot.press("escape")

        assert TodoWidget.recurrence in app.api.layouts.todo_layout

        await pilot.press("r")
        assert app.get_dooit_mode() == "INSERT"

        await pilot.press("1", "w", "enter")
        assert tree.current_model.recurrence == timedelta(weeks=1)


async def test_new_todo_reusing_deleted_child_id():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        app.api.vars.show_confirm = False

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("parent"), "escape")
        tree.add_child_node()
        await pilot.press(*list("child"), "escape")

        tree.highlighted = 0
        await pilot.press("x", "x")  # removes parent and child

        for name in ["one", "two"]:
            tree.add_sibling()
            await pilot.press(*list(name), "escape")

        assert [t.description for t in tree.model.todos] == ["one", "two"]
        shown = [tree._renderers[o.id].model.description for o in tree._options]
        assert shown == ["one", "two"]


async def test_paste_above_first_item():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        for name in "abc":
            tree.add_sibling()
            await pilot.press(name, "escape")

        await pilot.press("Y")  # copy c
        tree.highlighted = 0
        await pilot.press("P")  # paste above a

        assert [t.description for t in tree.model.todos] == ["c", "a", "b", "c"]
        assert tree.highlighted == 0


async def test_paste_goes_next_to_highlighted_item():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        for name in "pq":
            tree.add_sibling()
            await pilot.press(name, "escape")

        tree.highlighted = 0
        tree.add_child_node()
        await pilot.press(*list("child"), "escape")
        await pilot.press("Y")  # copy the nested child

        q = tree.model.todos[1]
        tree.highlight_id(q.uuid)
        await pilot.press("p")  # paste below q

        assert [t.description for t in tree.model.todos] == ["p", "q", "child"]
        assert [t.description for t in tree.model.todos[0].todos] == ["child"]
        assert tree.current_model.description == "child"
        assert tree.current_model.parent_workspace == tree.model


async def test_paste_after_original_was_deleted():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        app.api.vars.show_confirm = False

        tree = await create_and_move_to_todo(pilot)
        for name in "ab":
            tree.add_sibling()
            await pilot.press(name, "escape")

        tree.add_child_node()
        await pilot.press(*list("sub"), "escape")
        tree.highlighted = 1  # b

        await pilot.press("Y", "x", "x")  # cut b (with its child)
        await pilot.press("p")

        assert [t.description for t in tree.model.todos] == ["a", "b"]
        assert [t.description for t in tree.model.todos[1].todos] == ["sub"]


async def test_paste_into_empty_list():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        app.api.vars.show_confirm = False

        tree = await create_and_move_to_todo(pilot)
        tree.add_sibling()
        await pilot.press(*list("only"), "escape")

        await pilot.press("Y", "x", "x")
        assert len(tree._options) == 0

        await pilot.press("p")
        assert [t.description for t in tree.model.todos] == ["only"]
        assert tree.current_model.description == "only"


async def test_paste_with_empty_clipboard():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        tree.add_sibling()
        await pilot.press("a", "escape")

        assert tree.paste_model_from_clipboard() is None
        await pilot.pause()

        bar = app.bar_switcher.visible_content
        assert getattr(bar, "message", None) == "No model in clipboard"
        assert len(tree._options) == 1


async def test_non_number_effort():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        tree.add_sibling()
        await pilot.press("a", "escape")
        todo = tree.current_model

        await pilot.press("e", "backspace", "x", "-", "1", "enter")
        await pilot.pause()

        bar = app.bar_switcher.visible_content
        assert getattr(bar, "message", None) == "Effort must be a whole number"
        assert todo.effort == 0


async def test_new_item_without_description_is_discarded():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        tree.add_sibling()
        await pilot.press(*list("keep"), "escape")

        await pilot.press("a", "escape")  # new sibling, nothing typed
        assert [t.description for t in tree.model.todos] == ["keep"]
        assert tree.current_model.description == "keep"

        await pilot.press("A", "enter")  # new child, nothing typed
        assert tree.model.todos[0].todos == []

        # clearing an existing item's description keeps the item
        await pilot.press("i", *["backspace"] * 4, "escape")
        assert len(tree.model.todos) == 1


async def test_hide_completed_todos():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        for name in ["done", "open", "parent"]:
            tree.add_sibling()
            await pilot.press(*list(name), "escape")
        tree.add_child_node()
        await pilot.press(*list("finished step"), "escape", "c")
        tree.add_sibling()
        await pilot.press(*list("next step"), "escape")

        tree.highlighted = 0
        await pilot.press("c")  # complete "done"

        def shown():
            return [tree._renderers[o.id].model.description for o in tree._options]

        assert shown() == ["done", "open", "parent", "finished step", "next step"]

        await pilot.press("h")
        assert shown() == ["open", "parent", "next step"]
        assert tree.border_title == "Todos (completed hidden)"

        # completing a todo while hidden removes it from view
        await pilot.press("c")
        assert shown() == ["parent", "next step"]
        assert tree.current_model.description == "parent"

        # finishing the last step completes the parent, hiding both
        await pilot.press("j", "c")
        assert shown() == []
        assert tree.highlighted is None

        await pilot.press("h")
        assert tree.border_title == "Todos"
        assert len(shown()) == 5
        assert tree.highlighted is not None


async def test_hidden_history_has_no_expand_indicator():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        tree.add_sibling()
        await pilot.press(*list("rent"), "escape", "r", "1", "w", "enter", "c")
        todo = tree.current_model
        assert tree.is_collapsed_parent(todo)  # history entry

        await pilot.press("h")
        assert not tree.is_collapsed_parent(todo)
