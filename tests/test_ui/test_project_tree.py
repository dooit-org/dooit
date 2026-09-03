from pytest import raises
from textual.widgets import ContentSwitcher
from dooit.api.exceptions import NoNodeError
from dooit.ui.widgets.trees.todos_tree import TodosTree
from tests.test_ui.ui_base import (
    run_pilot,
    set_clipboard,
    tree_options,
    highlighted_index,
)
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
        # A project left without a description is discarded rather than kept,
        # so it has to be named before the edit is committed
        await pilot.press(*list("project"))
        await pilot.press("escape")

        # The pane opens on its fixed projects, and the redraw that follows an
        # edit puts the cursor back on the first of them: shifting is what
        # this is about, so the cursor goes back on the project first
        ptree.highlight_id(tree_options(ptree)[0].id)

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
        # Named before the edit is committed, or a blank project is discarded
        await pilot.press(*list("project"))
        await pilot.press("escape")

        # The second `add_sibling` was refused, so there is one project, and
        # it is the one the cursor can be put back on
        assert len(tree_options(ptree)) == 1

        ptree.highlight_id(tree_options(ptree)[0].id)
        assert highlighted_index(ptree) == 0


async def test_paste_as_sibling():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        ptree = app.project_tree

        # The app opens itself on the Today pane, on a message of its own, so
        # the focus is only where a test can rely on it once that has been
        # through and the projects pane has been asked for back
        await pilot.pause()
        app.api.focus_projects()
        await pilot.pause()

        set_clipboard(" pasted   project \n")

        # The first paste has nothing to sit beside, so it starts the tree
        await pilot.press("ctrl+v")
        await pilot.pause()

        assert len(tree_options(ptree)) == 1

        # A description is one line, whatever the clipboard was
        assert ptree.current_model.description == "pasted project"

        # And it is a description like any other: `i` opens the edit on the
        # pasted text rather than on the empty string the node was made as
        await pilot.press("i")
        await pilot.pause()
        assert ptree.current.description.value == "pasted project"

        await pilot.press("escape")
        await pilot.pause()
        assert ptree.current_model.description == "pasted project"

        await pilot.press("ctrl+v")
        await pilot.pause()

        assert len(tree_options(ptree)) == 2
        assert highlighted_index(ptree) == 1

        # Nothing on the clipboard is nothing to add
        set_clipboard("   ")
        await pilot.press("ctrl+v")
        await pilot.pause()

        assert len(tree_options(ptree)) == 2


async def test_copy_description():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        await pilot.pause()
        app.api.focus_projects()
        await pilot.pause()

        set_clipboard("nixos")
        await pilot.press("ctrl+v")
        await pilot.pause()

        await pilot.press("ctrl+c")
        await pilot.pause()

        assert app.clipboard == "nixos"
