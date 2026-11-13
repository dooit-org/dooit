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
