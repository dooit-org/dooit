from tests.test_ui.ui_base import run_pilot
from dooit.ui.tui import Dooit


async def test_bar_switcher():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        bar_switcher = app.bar_switcher
        wtree = app.workspace_tree
        wtree.add_sibling()

        await pilot.press("x", "escape")

        bar_switcher.switch_to_sort(wtree.current_model, wtree.sort)
        await pilot.pause()
        assert bar_switcher.current == "sort_bar"

        bar_switcher.switch_to_sort(wtree.current_model, wtree.sort)
        await pilot.pause()
        assert bar_switcher.current == "sort_bar"
