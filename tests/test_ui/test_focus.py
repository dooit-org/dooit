from asyncio import sleep
from tests.test_ui.ui_base import run_pilot
from dooit.ui.tui import Dooit
from dooit.ui.screens import FocusScreen, MainScreen
from dooit.ui.widgets.bars import FocusBar, StatusBar


async def open_focus_bar(pilot) -> FocusBar:
    app = pilot.app
    assert isinstance(app, Dooit)

    await pilot.press("f")
    await pilot.pause()

    bar = app.bar_switcher.visible_content
    assert isinstance(bar, FocusBar)
    return bar


async def test_focus_bar_arrows():
    async with run_pilot() as pilot:
        bar = await open_focus_bar(pilot)
        assert bar.minutes == 25

        await pilot.press("up")
        assert bar.minutes == 30

        await pilot.press("right", "right")
        assert bar.minutes == 32

        await pilot.press("up")
        assert bar.minutes == 35  # snaps to the next multiple of 5

        await pilot.press("left", "left", "down")
        assert bar.minutes == 30  # snaps to the previous multiple of 5

        for _ in range(10):
            await pilot.press("down")
        assert bar.minutes == 1

        await pilot.press("left")
        assert bar.minutes == 1

        await pilot.press("right")
        assert bar.minutes == 2


async def test_focus_bar_typing():
    async with run_pilot() as pilot:
        bar = await open_focus_bar(pilot)

        await pilot.press("4", "2")
        assert bar.minutes == 42

        await pilot.press("backspace")
        assert bar.minutes == 4

        await pilot.press("5")
        assert bar.minutes == 45

        await pilot.press("9", "9")
        assert bar.minutes == 459  # capped at 3 digits

        await pilot.press("right")
        assert bar.minutes == 460

        await pilot.press("7")
        assert bar.minutes == 7  # typing after arrows starts over


async def test_focus_bar_zero_does_not_start():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        bar = await open_focus_bar(pilot)
        await pilot.press("0", "enter")
        await pilot.pause()

        assert app.bar_switcher.visible_content is bar
        assert isinstance(app.screen, MainScreen)


async def test_focus_bar_cancel():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        await open_focus_bar(pilot)
        await pilot.press("escape")
        await pilot.pause()

        assert isinstance(app.bar_switcher.visible_content, StatusBar)
        assert isinstance(app.screen, MainScreen)


async def test_focus_session_starts():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        await open_focus_bar(pilot)
        await pilot.press("1", "0", "enter")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, FocusScreen)
        assert 599 <= screen.remaining <= 600

        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, MainScreen)


async def test_focus_session_finishes():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        screen = FocusScreen(1)
        await app.push_screen(screen)
        assert not screen.finished

        await sleep(1.5)
        await pilot.pause()

        assert screen.finished
        assert screen.has_class("-finished")
        assert screen.remaining_text == "0"


def test_remaining_text():
    assert FocusScreen(25 * 60).remaining_text == "25"
    assert FocusScreen(90).remaining_text == "2"  # rounded up
    assert FocusScreen(30).remaining_text == "1"
    assert FocusScreen(125 * 60).remaining_text == "125"


async def test_focus_on_highlighted_todo():
    from textual.widgets import Label
    from tests.test_ui.ui_base import create_and_move_to_todo

    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        tree.add_sibling()
        await pilot.press(*list("write report"), "escape")
        todo = tree.current_model

        bar = await open_focus_bar(pilot)
        assert bar.todo is todo
        assert "Focus on write report for" in bar.render().plain

        await pilot.press("enter")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, FocusScreen)
        assert screen.query_one("#focus_todo", Label).content == "write report"

        await pilot.press("c")
        await pilot.pause()

        assert isinstance(app.screen, MainScreen)
        assert todo.is_completed


async def test_focus_from_workspaces_is_a_plain_timer():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        app.workspace_tree.add_sibling()
        await pilot.press("w", "escape")

        bar = await open_focus_bar(pilot)
        assert bar.todo is None
        assert bar.render().plain.startswith(" Focus for ")

        await pilot.press("enter")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, FocusScreen)
        assert not screen.query("#focus_todo")

        await pilot.press("c")  # nothing to complete
        await pilot.pause()
        assert app.screen is screen


async def test_finished_session_offers_to_complete_todo():
    from textual.widgets import Label
    from tests.test_ui.ui_base import create_and_move_to_todo

    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)

        tree = await create_and_move_to_todo(pilot)
        tree.add_sibling()
        await pilot.press("t", "escape")

        screen = FocusScreen(1, tree.current_model)
        await app.push_screen(screen)
        hint = screen.query_one("#focus_hint", Label)
        assert not hint.display

        await sleep(1.5)
        await pilot.pause()
        assert hint.display
