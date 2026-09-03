from typing import List, Optional
from unittest.mock import patch
from textual.pilot import Pilot
from textual.widgets.option_list import Option
from textual.widgets import ContentSwitcher
from dooit.api import fixed_project_from_id
from dooit.ui.tui import Dooit
from dooit.ui.widgets.trees.model_tree import ModelTree
from dooit.ui.widgets.trees.todos_tree import TodosTree

TEMP_DB_PATH = ":memory:"

# The host's clipboard, which a test can neither be handed nor allowed to
# write over. Patched once, for the whole run: what dooit reads back is what a
# test last put here, and nothing else on the machine can change it underneath
_clipboard = ""


def set_clipboard(text: str) -> None:
    global _clipboard
    _clipboard = text


patch("dooit.utils.clipboard.pyperclip.paste", lambda: _clipboard).start()
patch("dooit.utils.clipboard.pyperclip.copy", lambda text: None).start()


def run_pilot():
    return Dooit(db_path=TEMP_DB_PATH).run_test()


async def create_and_move_to_todo(pilot: Pilot) -> TodosTree:
    app = pilot.app
    assert isinstance(app, Dooit)

    ptree = app.project_tree
    ptree.add_sibling()
    await pilot.pause()

    # A project left without a description is discarded rather than kept, so
    # it has to be named before the edit is committed
    await pilot.press(*list("project"))
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
    """
    Options of a tree that stand for a stored model

    The column titles, the rules and the fixed projects are all furniture the
    pane came with; what the tests count is what they put in it.
    """

    return [
        option
        for option in tree._options
        if not tree.is_static_row(option.id)
        and fixed_project_from_id(option.id or "") is None
    ]


def highlighted_index(tree: ModelTree) -> Optional[int]:
    """Index of the highlighted node among the stored rows alone"""

    if tree.highlighted is None:
        return None

    # Counted by looking the row up among the stored ones rather than by
    # subtracting what sits above it: the furniture is not all in one place,
    # since a pane can pin a block of its own below the stored rows
    highlighted = tree._options[tree.highlighted]
    options = tree_options(tree)

    if highlighted not in options:
        return None

    return options.index(highlighted)
