from tests.test_ui.ui_base import run_pilot, create_and_move_to_todo
from dooit.ui.tui import Dooit
from dooit.ui.widgets.bars import SortBar
from dooit.ui.widgets.trees.todos_tree import TodosTree
from dooit.ui.widgets.trees.workspaces_tree import WorkspacesTree


async def test_arrows_switch_focus():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        await create_and_move_to_todo(pilot)
        assert isinstance(app.focused, TodosTree)

        await pilot.press("right")
        assert isinstance(app.focused, TodosTree)

        await pilot.press("left")
        assert isinstance(app.focused, WorkspacesTree)

        await pilot.press("left")
        assert isinstance(app.focused, WorkspacesTree)

        await pilot.press("right")
        assert isinstance(app.focused, TodosTree)


async def test_right_without_todos_tree():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        await pilot.press("right")
        assert isinstance(app.focused, WorkspacesTree)


async def test_shift_arrows_move_item():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        for name in "ab":
            tree.add_sibling()
            await pilot.press(name, "escape")

        def descriptions():
            return [t.description for t in tree.model.todos]

        assert descriptions() == ["a", "b"]
        assert tree.current_model.description == "b"

        await pilot.press("shift+up")
        assert descriptions() == ["b", "a"]
        assert tree.current_model.description == "b"

        await pilot.press("shift+down")
        assert descriptions() == ["a", "b"]
        assert tree.current_model.description == "b"


async def test_s_starts_sort():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        tree.add_sibling()
        await pilot.press("escape")

        await pilot.press("s")
        await pilot.pause()
        assert isinstance(app.bar_switcher.visible_content, SortBar)


async def test_q_quits():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running
