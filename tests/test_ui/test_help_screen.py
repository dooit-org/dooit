from dooit.ui.bridge.events import SpawnHelp
from dooit.ui.screens import HelpScreen, MainScreen
from dooit.ui.tui import Dooit
from tests.test_ui.ui_base import run_pilot


async def test_help_screen_mount():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        app.api.keys.set("X", app.api.no_op)  # test cover no_op
        app.api.keys.set("Y", app.api.move_up)  # group test

        # test if help screen is mounted
        await app.push_screen("help")
        assert isinstance(app.screen, HelpScreen)

        await app.push_screen("main")

        # test with keybinding
        await pilot.press("?")
        assert isinstance(app.screen, HelpScreen)
        await app.push_screen("main")

        # test function
        assert isinstance(app.screen, MainScreen)
        await app.screen.spawn_help(SpawnHelp())
        assert isinstance(app.screen, HelpScreen)
