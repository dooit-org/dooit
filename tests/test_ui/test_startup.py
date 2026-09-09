from dooit.api import TODAY
from dooit.ui.tui import Dooit
from dooit.ui.widgets.trees.fixed_todos_tree import FixedTodosTree
from tests.test_ui.ui_base import boot, run_pilot


async def test_startup():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        assert app.is_running

        # check for vars
        app.bar_switcher
        app.project_tree

        assert app.get_dooit_mode() == "NORMAL"


async def test_mode_follows_editing():
    """The bar's mode pill: NORMAL on the trees, INSERT inside an edit"""

    async with run_pilot() as pilot:
        app = await boot(pilot)

        assert app.get_dooit_mode() == "NORMAL"

        await pilot.press("j", "n")
        await pilot.pause()
        assert app.get_dooit_mode() == "INSERT"

        await pilot.press(*list("project"))
        await pilot.press("enter")
        await pilot.pause()
        assert app.get_dooit_mode() == "NORMAL"


async def test_dooit_opens_on_today():
    """The day's work is the first thing on screen, focused"""

    async with run_pilot() as pilot:
        app = await boot(pilot)

        tree = app.focused
        assert isinstance(tree, FixedTodosTree)
        assert tree.model is TODAY

        # The projects cursor points at the same place the pane shows
        assert app.project_tree.current_model is TODAY
