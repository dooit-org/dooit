from typing import List, Optional
from unittest.mock import patch

from textual.pilot import Pilot
from textual.widgets import ContentSwitcher
from textual.widgets.option_list import Option

from dooit.api import Project, Todo, fixed_project_from_id
from dooit.ui.tui import Dooit
from dooit.ui.widgets.trees.fixed_todos_tree import FixedTodosTree
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
    # Expansion state lives on the tree *class* and model uuids repeat
    # between one :memory: database and the next, so a row expanded in one
    # test would come up expanded in another
    from dooit.ui.widgets.trees.base_tree import BaseTree

    BaseTree.expanded_nodes.clear()

    return Dooit(db_path=TEMP_DB_PATH).run_test(size=(120, 36))


async def boot(pilot: Pilot) -> Dooit:
    """
    Waits out the startup jump to the Today pane

    The app opens itself on Today with a `call_after_refresh`, so for the
    first few pauses of a test the cursor and the focus are still on their way
    there. Every test starts from the state the user actually sees: the Today
    pane in front, focused, and the projects cursor on the Today row.
    """

    app = pilot.app
    assert isinstance(app, Dooit)

    for _ in range(20):
        await pilot.pause()

        tree = visible_todos_or_none(app)
        if isinstance(tree, FixedTodosTree) and app.focused is tree:
            return app

    raise AssertionError("The app never settled on the Today pane")


def visible_todos_or_none(app: Dooit) -> Optional[TodosTree]:
    """The tasks pane in front, or None while the dashboard is showing"""

    content = app.screen.query_one(
        "#todo_switcher", expect_type=ContentSwitcher
    ).visible_content

    if isinstance(content, TodosTree):
        return content

    return None


def visible_todos(app: Dooit) -> TodosTree:
    tree = visible_todos_or_none(app)
    assert tree is not None, "No tasks pane is in front"
    return tree


async def commit_line(pilot: Pilot, text: str) -> None:
    """
    Types `text` into the open edit and commits it

    Enter is what keeps an edit; escape throws it away, and a brand new item
    thrown away without a name is dropped entirely.
    """

    if text:
        await pilot.press(*list(text))

    await pilot.press("enter")
    await pilot.pause()


async def new_project(pilot: Pilot, name: str) -> Project:
    """
    Creates a top-level project the way the user does: `j`, `n`, name, enter

    Leaves the cursor on the new project, with its (empty) tasks pane in
    front, and the projects pane focused.
    """

    app = pilot.app
    assert isinstance(app, Dooit)

    await pilot.press("j", "n")
    await commit_line(pilot, name)

    project = app.project_tree.current_model
    assert isinstance(project, Project)
    assert project.description == name

    return project


async def new_todo(pilot: Pilot, name: str) -> Todo:
    """
    Creates a todo in the open project's pane: `ö`, `n`, name, enter

    Assumes a stored project's pane is in front (the state `new_project`
    leaves behind). Leaves the cursor on the new todo, pane focused.
    """

    app = pilot.app
    assert isinstance(app, Dooit)

    await pilot.press("ö", "n")
    await commit_line(pilot, name)

    tree = visible_todos(app)
    todo = tree.current_model
    assert isinstance(todo, Todo)
    assert todo.description == name

    return todo


async def create_and_move_to_todo(pilot: Pilot) -> TodosTree:
    """
    A named project with its empty tasks pane in front and focused

    The smallest start most todo tests share.
    """

    app = await boot(pilot)
    await new_project(pilot, "project")
    await pilot.press("ö")
    await pilot.pause()

    tree = visible_todos(app)
    assert app.focused is tree

    return tree


def tree_options(tree: ModelTree) -> List[Option]:
    """
    Options of a tree that stand for a stored model

    The column titles, the rules, the group headings and the fixed projects
    are all furniture the pane came with; what the tests count is what they
    put in it.
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


def notification_message(app: Dooit) -> Optional[str]:
    """What the bar is saying right now, if it is saying anything"""

    if app.bar_switcher.current != "notification_bar":
        return None

    return app.bar_switcher.visible_content.message
