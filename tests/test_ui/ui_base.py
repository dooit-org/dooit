from textual.pilot import Pilot
from textual.widgets import ContentSwitcher
from dooit.ui.tui import Dooit
from dooit.ui.widgets.trees.todos_tree import TodosTree

TEMP_DB_PATH = ":memory:"


def run_pilot():
    return Dooit(db_path=TEMP_DB_PATH).run_test()


async def create_and_move_to_todo(pilot: Pilot) -> TodosTree:
    app = pilot.app
    assert isinstance(app, Dooit)

    wtree = app.workspace_tree
    wtree.add_sibling()
    await pilot.pause()

    await pilot.press("w", "escape")
    await pilot.pause()

    app.api.switch_focus()
    await pilot.pause()

    tree = app.screen.query_one(
        "#todo_switcher", expect_type=ContentSwitcher
    ).visible_content
    assert isinstance(tree, TodosTree)

    return tree
