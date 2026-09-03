from pytest import raises
from textual.widgets import ContentSwitcher
from dooit.api.exceptions import NoNodeError
from dooit.ui.widgets.trees.todos_tree import TodosTree
from tests.test_ui.ui_base import run_pilot, tree_options, highlighted_index
from dooit.ui.tui import Dooit


async def test_projects_tree():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        ptree = app.project_tree

        assert len(tree_options(ptree)) == 0

        # basic addition
        ptree.add_project()
        ptree.add_project()
        ptree.add_project()
        p = ptree.add_project()

        assert len(tree_options(ptree)) == 4

        # highlights
        ptree.highlight_id(p)
        assert highlighted_index(ptree) == 3  # n-1

        await pilot.pause()

        current = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert current is not None
        assert current.id == TodosTree(ptree.current_model).id

        ptree.toggle_expand_parent()
        assert highlighted_index(ptree) == 3  # no change

        # child nodes
        p = ptree.add_child_node()
        assert len(tree_options(ptree)) == 5
        assert highlighted_index(ptree) == 4

        # nested nodes
        ptree.toggle_expand()
        assert len(tree_options(ptree)) == 5

        ptree.toggle_expand_parent()
        assert len(tree_options(ptree)) == 4

        ptree.toggle_expand()
        assert len(tree_options(ptree)) == 5


async def test_base_addition():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        ptree = app.project_tree

        ptree.add_sibling()
        assert highlighted_index(ptree) == 0
        await pilot.press("escape")
        await pilot.pause()

        ptree.add_sibling()
        assert highlighted_index(ptree) == 1


async def test_project_remove_cancelled():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        ptree = app.project_tree

        ptree.add_sibling()
        await pilot.press("escape")
        ptree.add_sibling()
        await pilot.press("escape")

        p1 = ptree.current_model

        current = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert current is not None
        assert current.id == TodosTree(p1).id

        ptree.remove_node()
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()

        p2 = ptree.current_model
        current = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert current is not None
        assert current.id == TodosTree(p2).id

        assert p1.id == p2.id


async def test_project_remove():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        ptree = app.project_tree

        ptree.add_sibling()
        await pilot.press("escape")
        ptree.add_sibling()
        await pilot.press("escape")

        p1 = ptree.current_model

        current = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert current is not None
        assert current.id == TodosTree(p1).id

        ptree.remove_node()
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()

        p2 = ptree.current_model
        current = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert current is not None
        assert current.id == TodosTree(p2).id

        assert p1.id != p2.id


async def test_no_node_error():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        ptree = app.project_tree

        with raises(NoNodeError):
            ptree.remove_node()


async def test_shifts_single_item():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        ptree = app.project_tree

        ptree.add_sibling()
        await pilot.press("escape")

        ptree.shift_up()
        await pilot.pause()

        assert highlighted_index(ptree) == 0

        ptree.shift_down()
        await pilot.pause()

        assert highlighted_index(ptree) == 0


async def test_shifts():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        ptree = app.project_tree

        ptree.add_sibling()
        await pilot.press("escape")
        ptree.add_sibling()
        await pilot.press("escape")
        ptree.highlighted = ptree.first_selectable_index

        # shift up with first index
        ptree.shift_up()
        await pilot.pause()

        assert highlighted_index(ptree) == 0

        # shift down with first index
        ptree.shift_down()
        await pilot.pause()

        assert highlighted_index(ptree) == 1

        # shift down with last index
        ptree.shift_down()
        await pilot.pause()

        assert highlighted_index(ptree) == 1

        # shift down with last index
        ptree.shift_up()
        await pilot.pause()

        assert highlighted_index(ptree) == 0


async def test_cursor_movements():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        ptree = app.project_tree

        ptree.add_sibling()
        await pilot.press("escape")

        ptree.add_sibling()
        await pilot.press("escape")

        assert highlighted_index(ptree) == 1

        ptree.action_cursor_down()
        assert highlighted_index(ptree) == 1

        ptree.action_cursor_up()
        assert highlighted_index(ptree) == 0

        ptree.action_cursor_up()
        assert highlighted_index(ptree) == 0

        ptree.action_cursor_down()
        assert highlighted_index(ptree) == 1

        # clicking should not affect the highlight
        for x in range(5):
            for y in range(5):
                await pilot.click(ptree, offset=(x, y))
                assert highlighted_index(ptree) == 1


async def test_add_sibling_while_editing():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        ptree = app.project_tree

        ptree.add_sibling()
        # await pilot.press("escape") # Dont stop editing

        ptree.add_sibling()
        await pilot.press("escape")
        assert highlighted_index(ptree) == 0

        assert len(tree_options(ptree)) == 1


async def test_yank_and_paste_project():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        ptree = app.project_tree

        # Create first project
        ptree.add_sibling()
        await pilot.press(*list("project 1"))
        await pilot.press("escape")

        # Create child project to test nested cloning
        ptree.add_child_node()
        await pilot.press(*list("child project"))
        await pilot.press("escape")

        # Go back to parent
        ptree.action_cursor_up()
        await pilot.pause()

        # Add a todo to the project
        app.api.switch_focus()
        await pilot.pause()

        tree = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert isinstance(tree, TodosTree)

        tree.add_sibling()
        await pilot.press(*list("todo in project"))
        await pilot.press("escape")
        assert len(tree_options(tree)) == 1

        # Switch back to project tree
        app.api.switch_focus()
        await pilot.pause()

        # Yank the project
        await pilot.press("Y")
        await pilot.pause()

        # Paste it
        await pilot.press("v")
        await pilot.pause()

        # Check that the project was cloned
        assert len(tree_options(ptree)) == 3

        # Verify child project was cloned
        ptree.toggle_expand()
        await pilot.pause()
        assert len(tree_options(ptree)) == 4

        # Check that todo was cloned by switching to todo tree
        app.api.switch_focus()
        await pilot.pause()

        tree = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert isinstance(tree, TodosTree)

        assert len(tree_options(tree)) == 1
