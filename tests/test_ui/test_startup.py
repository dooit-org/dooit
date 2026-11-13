from textual.widgets import ContentSwitcher
from dooit.api import Workspace
from tests.test_ui.ui_base import run_pilot
from dooit.ui.tui import Dooit
from dooit.ui.widgets.trees.todos_tree import TodosTree


async def test_startup():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        assert app.is_running

        # check for vars
        app.bar_switcher
        app.workspace_tree

        assert app.get_dooit_mode() == "NORMAL"


async def test_first_items_highlighted_on_startup(tmp_path):
    db_path = str(tmp_path / "dooit.db")

    async with Dooit(db_path=db_path).run_test() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        first = Workspace.from_id(app.workspace_tree.add_workspace())
        app.workspace_tree.add_workspace()
        first.add_todo()
        first.add_todo()

    async with Dooit(db_path=db_path).run_test() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        await pilot.pause()
        assert app.workspace_tree.highlighted == 0

        todos_tree = app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        ).visible_content
        assert isinstance(todos_tree, TodosTree)
        assert todos_tree.highlighted == 0
