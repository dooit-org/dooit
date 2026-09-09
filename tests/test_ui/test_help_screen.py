"""
The help screen: the keybinds of the config, grouped the way it groups them
"""

from dooit.ui.api.events import SpawnHelp
from dooit.ui.screens import HelpScreen, MainScreen
from dooit.ui.screens.help import DooitKeyTable
from tests.test_ui.ui_base import boot, run_pilot


async def test_help_screen_mount():
    async with run_pilot() as pilot:
        # Settled first: the startup jump to Today lands as a message, and one
        # arriving while the help screen is on top finds no projects pane to
        # move the cursor in
        app = await boot(pilot)

        app.api.keys.set("X", app.api.no_op)  # test cover no_op
        app.api.keys.set("Z", app.api.move_up, group="test")  # group test

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


async def test_help_lists_the_config_groups_in_order():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        assert app.api.keys.groups == [
            "Navigation",
            "Editing",
            "Priority & Effort",
            "Moving & Clipboard",
            "Search & View",
            "App",
        ]


async def test_every_visible_keybind_has_a_row():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await app.push_screen("help")
        table = app.screen.query_one(DooitKeyTable)

        rows = {
            label: description
            for group in app.api.keys.groups
            for label, description in table._rows(group)
        }

        # A spot check across the groups: one key per feature family
        for label in ("j", "gt", "n", "C", "space", "xx", "YY", "/", "o", "q"):
            assert label in rows, label

        # The scales collapse to one row each instead of four
        assert "p0-p3" in rows
        assert "p1" not in rows
        assert "e0-e3" in rows

        # So do the sort chords
        assert "SP/SD/SS" in rows
        assert "SP" not in rows

        # Named keys are written without their angle brackets
        assert "ctrl+q" in rows
        assert "ctrl+c" in rows


async def test_hidden_keybinds_stay_out_of_the_help():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await app.push_screen("help")
        table = app.screen.query_one(DooitKeyTable)

        labels = [
            label
            for group in app.api.keys.groups
            for label, _ in table._rows(group)
        ]

        # `?` itself is hidden: the key that opened the window is not news
        assert "?" not in labels
