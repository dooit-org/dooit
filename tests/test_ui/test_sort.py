from asyncio import sleep
from pytest import raises
from dooit.api.exceptions import NoNodeError
from dooit.ui.widgets.bars import SortBar

from dooit.ui.widgets.bars.status_bar.bar import StatusBar
from tests.test_ui.ui_base import (
    run_pilot,
    create_and_move_to_todo,
    todo_options,
    highlighted_index,
)
from dooit.ui.tui import Dooit


async def test_search_on_workspace():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        api = app.api

        wtree = app.workspace_tree

        with raises(NoNodeError):
            api.start_sort()

        wtree.add_sibling()
        await pilot.press(*list("zzz"))
        await pilot.press("escape")

        api.start_sort()
        await pilot.pause()

        sort_bar = app.bar_switcher.visible_content
        assert isinstance(sort_bar, SortBar)

        assert len(sort_bar.options) == 2  # reverse and description


async def test_search_on_todo():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        api = app.api

        tree = await create_and_move_to_todo(pilot)

        with raises(NoNodeError):
            api.start_sort()

        tree.add_sibling()
        await pilot.press("escape")

        api.start_sort()
        await pilot.pause()

        sort_bar = app.bar_switcher.visible_content
        assert isinstance(sort_bar, SortBar)

        assert len(sort_bar.options) == 7  # reverse and description


async def test_options_highlight():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        api = app.api

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press("escape")

        api.start_sort()
        await pilot.pause()

        sort_bar = app.bar_switcher.visible_content
        assert isinstance(sort_bar, SortBar)

        assert sort_bar.selected == 0

        await pilot.press("left")
        assert sort_bar.selected == 0

        await pilot.press("right")
        assert sort_bar.selected == 1


async def test_reverse_sort():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        api = app.api

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("zzz"))
        await pilot.press("escape")

        tree.add_sibling()
        await pilot.press(*list("abcd"))
        await pilot.press("escape")

        current_options = [node.id for node in todo_options(tree)]

        api.start_sort()
        await pilot.pause()

        sort_bar = app.bar_switcher.visible_content
        assert isinstance(sort_bar, SortBar)
        assert highlighted_index(tree) == 1  # sorted in reverse

        await pilot.press("enter")
        await pilot.pause()
        current_bar = app.bar_switcher.visible_content
        assert isinstance(current_bar, StatusBar)

        new_options = [node.id for node in todo_options(tree)]
        assert current_options != new_options
        await sleep(0.2)
        await pilot.pause()
        assert highlighted_index(tree) == 0  # sorted in reverse


async def test_sort_cancelled():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        api = app.api

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("zzz"))
        await pilot.press("escape")

        tree.add_sibling()
        await pilot.press(*list("abcd"))
        await pilot.press("escape")

        current_options = [node.id for node in todo_options(tree)]

        api.start_sort()
        await pilot.pause()

        sort_bar = app.bar_switcher.visible_content
        assert isinstance(sort_bar, SortBar)
        assert highlighted_index(tree) == 1  # sorted in reverse

        await pilot.press("escape")
        await pilot.pause()
        current_bar = app.bar_switcher.visible_content
        assert isinstance(current_bar, StatusBar)

        new_options = [node.id for node in todo_options(tree)]
        assert current_options == new_options


async def test_description_sort():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        api = app.api

        tree = await create_and_move_to_todo(pilot)

        tree.add_sibling()
        await pilot.press(*list("zzz"))
        await pilot.press("escape")

        tree.add_sibling()
        await pilot.press(*list("abcd"))
        await pilot.press("escape")

        api.start_sort()
        await pilot.pause()

        sort_bar = app.bar_switcher.visible_content
        assert isinstance(sort_bar, SortBar)
        assert highlighted_index(tree) == 1  # sorted in reverse
        current_options = [node.id for node in todo_options(tree)]

        sort_bar.selected = 1
        await pilot.press("enter")
        await pilot.pause()
        current_bar = app.bar_switcher.visible_content
        assert isinstance(current_bar, StatusBar)

        new_options = [node.id for node in todo_options(tree)]
        assert current_options == new_options[::-1]
        await sleep(0.2)
        await pilot.pause()
        assert highlighted_index(tree) == 0
