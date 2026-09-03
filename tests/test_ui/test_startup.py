from tests.test_ui.ui_base import run_pilot
from dooit.ui.tui import Dooit


async def test_startup():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        assert app.is_running

        # check for vars
        app.bar_switcher
        app.project_tree

        assert app.get_dooit_mode() == "NORMAL"
