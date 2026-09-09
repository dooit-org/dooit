"""
Moving around: pane focus, cursor keys, and the jumps to the fixed projects
"""

from dooit.api import BIN, COMPLETED, TODAY, UPCOMING
from tests.test_ui.ui_base import (
    boot,
    commit_line,
    create_and_move_to_todo,
    highlighted_index,
    new_project,
    run_pilot,
    visible_todos,
)


async def test_focus_keys():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await pilot.press("j")
        assert app.focused is app.project_tree

        await pilot.press("ö")
        assert app.focused is visible_todos(app)

        await pilot.press("j")
        assert app.focused is app.project_tree


async def test_cursor_moves_in_the_todos_pane():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        for name in ("one", "two", "three"):
            await pilot.press("n")
            await commit_line(pilot, name)

        assert highlighted_index(tree) == 2

        await pilot.press("k")
        assert highlighted_index(tree) == 1

        await pilot.press("k")
        assert highlighted_index(tree) == 0

        # The header above the first row is furniture, not a place to stop
        await pilot.press("k")
        assert highlighted_index(tree) == 0

        await pilot.press("l")
        assert highlighted_index(tree) == 1

        await pilot.press("l", "l")
        assert highlighted_index(tree) == 2


async def test_top_and_bottom_of_the_todos_pane():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        for name in ("one", "two", "three"):
            await pilot.press("n")
            await commit_line(pilot, name)

        await pilot.press("g", "g")
        await pilot.pause()
        assert highlighted_index(tree) == 0

        await pilot.press("G")
        await pilot.pause()
        assert highlighted_index(tree) == 2


async def test_goto_today():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        await new_project(pilot, "elsewhere")

        await pilot.press("g", "t")
        await pilot.pause()

        tree = visible_todos(app)
        assert tree.model is TODAY
        assert app.focused is tree
        assert app.project_tree.current_model is TODAY


async def test_goto_upcoming():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await pilot.press("g", "u")
        await pilot.pause()

        assert visible_todos(app).model is UPCOMING
        assert app.project_tree.current_model is UPCOMING


async def test_goto_completed():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await pilot.press("g", "c")
        await pilot.pause()

        assert visible_todos(app).model is COMPLETED
        assert app.project_tree.current_model is COMPLETED


async def test_goto_bin():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await pilot.press("g", "b")
        await pilot.pause()

        assert visible_todos(app).model is BIN
        assert app.project_tree.current_model is BIN


async def test_goto_lands_on_the_first_task():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        await create_and_move_to_todo(pilot)

        await pilot.press("n")
        await commit_line(pilot, "planned")
        await pilot.press("s")
        await commit_line(pilot, "today")

        await pilot.press("g", "t")
        await pilot.pause()

        today_tree = visible_todos(app)
        assert today_tree.model is TODAY
        assert today_tree.current_model.description == "planned"


async def test_selecting_a_project_shows_its_pane():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        first = await new_project(pilot, "first")
        second = await new_project(pilot, "second")

        ptree.highlight_id(first.uuid)
        await pilot.pause()
        assert visible_todos(app).model.uuid == first.uuid

        ptree.highlight_id(second.uuid)
        await pilot.pause()
        assert visible_todos(app).model.uuid == second.uuid


async def test_row_shading_toggle():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        assert app.api.vars.row_shading is False

        await pilot.press("q")
        await pilot.pause()
        assert app.api.vars.row_shading is True

        await pilot.press("q")
        await pilot.pause()
        assert app.api.vars.row_shading is False


async def test_shaded_rows_alternate():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        for name in ("one", "two", "three", "four"):
            await pilot.press("n")
            await commit_line(pilot, name)

        await pilot.press("q")
        await pilot.pause()

        # Every other row, starting unshaded
        assert tree._shaded_rows == {1, 3}
