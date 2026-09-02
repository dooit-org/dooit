from typing import List, Optional
from textual.pilot import Pilot
from textual.widgets.option_list import Option
from textual.widgets import ContentSwitcher
from dooit.ui.tui import Dooit
from dooit.ui.widgets.trees.model_tree import ModelTree
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

    # A workspace left without a description is discarded rather than kept, so
    # it has to be named before the edit is committed
    await pilot.press(*list("workspace"))
    await pilot.press("escape")
    await pilot.pause()

    app.api.switch_focus()
    await pilot.pause()

    tree = app.screen.query_one(
        "#todo_switcher", expect_type=ContentSwitcher
    ).visible_content
    assert isinstance(tree, TodosTree)

    return tree


def tree_options(tree: ModelTree) -> List[Option]:
    """Options of a tree, without the column header row"""

    return [option for option in tree._options if option.id != tree.HEADER_ID]


def highlighted_index(tree: ModelTree) -> Optional[int]:
    """Index of the highlighted node, ignoring the column header row"""

    if tree.highlighted is None:
        return None

    header_rows = len(tree._options) - len(tree_options(tree))
    return tree.highlighted - header_rows
