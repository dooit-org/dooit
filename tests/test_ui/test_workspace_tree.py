from pytest import raises
from textual.widgets import ContentSwitcher
from dooit.api.exceptions import NoNodeError
from dooit.ui.widgets.trees.todos_tree import TodosTree
from tests.test_ui.ui_base import run_pilot
from dooit.ui.tui import Dooit


async def test_workspaces_tree():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        wtree = app.workspace_tree

        assert len(wtree._options) == 0

        # basic addition
        wtree.add_workspace()
        wtree.add_workspace()
        wtree.add_workspace()
        w = wtree.add_workspace()

        assert len(wtree._options) == 4

        # highlights
        wtree.highlight_id(w)
        assert wtree.highlighted == 3  # n-1

        await pilot.pause()

        current = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert current is not None
        assert current.id == TodosTree(wtree.current_model).id

        wtree.toggle_expand_parent()
        assert wtree.highlighted == 3  # no change

        # child nodes
        w = wtree.add_child_node()
        assert len(wtree._options) == 5
        assert wtree.highlighted == 4

        # nested nodes
        wtree.toggle_expand()
        assert len(wtree._options) == 5

        wtree.toggle_expand_parent()
        assert len(wtree._options) == 4

        wtree.toggle_expand()
        assert len(wtree._options) == 5


async def test_base_addition():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        wtree = app.workspace_tree

        wtree.add_sibling()
        assert wtree.highlighted == 0
        await pilot.press("escape")
        await pilot.pause()

        wtree.add_sibling()
        assert wtree.highlighted == 1


async def test_workspace_remove_cancelled():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        wtree = app.workspace_tree

        wtree.add_sibling()
        await pilot.press("escape")
        wtree.add_sibling()
        await pilot.press("escape")

        w1 = wtree.current_model

        current = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert current is not None
        assert current.id == TodosTree(w1).id

        wtree.remove_node()
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()

        w2 = wtree.current_model
        current = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert current is not None
        assert current.id == TodosTree(w2).id

        assert w1.id == w2.id


async def test_workspace_remove():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        wtree = app.workspace_tree

        wtree.add_sibling()
        await pilot.press("escape")
        wtree.add_sibling()
        await pilot.press("escape")

        w1 = wtree.current_model

        current = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert current is not None
        assert current.id == TodosTree(w1).id

        wtree.remove_node()
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()

        w2 = wtree.current_model
        current = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert current is not None
        assert current.id == TodosTree(w2).id

        assert w1.id != w2.id


async def test_no_node_error():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        wtree = app.workspace_tree

        with raises(NoNodeError):
            wtree.remove_node()


async def test_shifts_single_item():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        wtree = app.workspace_tree

        wtree.add_sibling()
        await pilot.press("escape")

        wtree.shift_up()
        await pilot.pause()

        assert wtree.highlighted == 0

        wtree.shift_down()
        await pilot.pause()

        assert wtree.highlighted == 0


async def test_shifts():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        wtree = app.workspace_tree

        wtree.add_sibling()
        await pilot.press("escape")
        wtree.add_sibling()
        await pilot.press("escape")
        wtree.highlighted = 0

        # shift up with first index
        wtree.shift_up()
        await pilot.pause()

        assert wtree.highlighted == 0

        # shift down with first index
        wtree.shift_down()
        await pilot.pause()

        assert wtree.highlighted == 1

        # shift down with last index
        wtree.shift_down()
        await pilot.pause()

        assert wtree.highlighted == 1

        # shift down with last index
        wtree.shift_up()
        await pilot.pause()

        assert wtree.highlighted == 0


async def test_cursor_movements():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        wtree = app.workspace_tree

        wtree.add_sibling()
        await pilot.press("escape")

        wtree.add_sibling()
        await pilot.press("escape")

        assert wtree.highlighted == 1

        wtree.action_cursor_down()
        assert wtree.highlighted == 1

        wtree.action_cursor_up()
        assert wtree.highlighted == 0

        wtree.action_cursor_up()
        assert wtree.highlighted == 0

        wtree.action_cursor_down()
        assert wtree.highlighted == 1

        # clicking should not affect the highlight
        for x in range(5):
            for y in range(5):
                await pilot.click(wtree, offset=(x, y))
                assert wtree.highlighted == 1


async def test_add_sibling_while_editing():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        wtree = app.workspace_tree

        wtree.add_sibling()
        # await pilot.press("escape") # Dont stop editing

        wtree.add_sibling()
        await pilot.press("escape")
        assert wtree.highlighted == 0

        assert len(wtree._options) == 1


async def test_yank_and_paste_workspace():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        wtree = app.workspace_tree

        # Create first workspace
        wtree.add_sibling()
        await pilot.press(*list("workspace 1"))
        await pilot.press("escape")

        # Create child workspace to test nested cloning
        wtree.add_child_node()
        await pilot.press(*list("child workspace"))
        await pilot.press("escape")

        # Go back to parent
        wtree.action_cursor_up()
        await pilot.pause()

        # Add a todo to the workspace
        app.api.switch_focus()
        await pilot.pause()

        tree = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert isinstance(tree, TodosTree)

        tree.add_sibling()
        await pilot.press(*list("todo in workspace"))
        await pilot.press("escape")
        assert tree.option_count == 1

        # Switch back to workspace tree
        app.api.switch_focus()
        await pilot.pause()

        # Yank the workspace
        await pilot.press("Y")
        await pilot.pause()

        # Paste it
        await pilot.press("p")
        await pilot.pause()

        # Check that the workspace was cloned
        assert wtree.option_count == 3

        # Verify child workspace was cloned
        wtree.toggle_expand()
        await pilot.pause()
        assert wtree.option_count == 4

        # Check that todo was cloned by switching to todo tree
        app.api.switch_focus()
        await pilot.pause()

        tree = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert isinstance(tree, TodosTree)

        assert tree.option_count == 1
