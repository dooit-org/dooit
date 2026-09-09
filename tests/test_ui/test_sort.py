"""
The order a project's tasks are read in: the SP / SD / SS chords

The order belongs to the pane, not to a project: it holds across projects
until it is switched again. Fixed projects order their own rows and turn the
chords down. (The old modal sort bar these chords replaced has no key bound
to it any more.)
"""

from dooit.api import Todo
from tests.test_ui.ui_base import (
    boot,
    commit_line,
    create_and_move_to_todo,
    new_project,
    notification_message,
    run_pilot,
    tree_options,
)


async def seed_unsorted(pilot):
    """Three todos whose filing order disagrees with every other order"""

    for name in ("beta", "alpha", "gamma"):
        await pilot.press("n")
        await commit_line(pilot, name)

    beta, alpha, gamma = Todo.all()

    alpha.priority = 3
    alpha.save()
    gamma.priority = 1
    gamma.save()

    from datetime import datetime

    beta.due = datetime(2030, 5, 1)
    beta.save()
    gamma.due = datetime(2030, 1, 1)
    gamma.save()

    beta.scheduled = datetime(2030, 3, 1)
    beta.save()
    alpha.scheduled = datetime(2030, 2, 1)
    alpha.save()

    # The field listeners redraw every pane once the writes have landed
    await pilot.pause()

    return beta, alpha, gamma


def visible_descriptions(tree) -> list:
    return [tree._renderers[o.id].model.description for o in tree_options(tree)]


async def test_the_default_order_is_priority():
    async with run_pilot() as pilot:
        app = pilot.app
        tree = await create_and_move_to_todo(pilot)

        assert app.api.vars.todo_sort == "priority"

        await seed_unsorted(pilot)

        # p1 first, p3 after, and the unprioritized past the end
        assert visible_descriptions(tree) == ["gamma", "alpha", "beta"]


async def test_sort_by_due():
    async with run_pilot() as pilot:
        app = pilot.app
        tree = await create_and_move_to_todo(pilot)
        await seed_unsorted(pilot)

        await pilot.press("S", "D")
        await pilot.pause()

        assert app.api.vars.todo_sort == "due"
        # The dated rows by date, and the undated one past the end
        assert visible_descriptions(tree) == ["gamma", "beta", "alpha"]

        message = notification_message(app)
        assert message is not None and "due date" in message


async def test_sort_by_scheduled():
    async with run_pilot() as pilot:
        app = pilot.app
        tree = await create_and_move_to_todo(pilot)
        await seed_unsorted(pilot)

        await pilot.press("S", "S")
        await pilot.pause()

        assert app.api.vars.todo_sort == "scheduled"
        assert visible_descriptions(tree) == ["alpha", "beta", "gamma"]


async def test_sort_back_to_priority():
    async with run_pilot() as pilot:
        app = pilot.app
        tree = await create_and_move_to_todo(pilot)
        await seed_unsorted(pilot)

        await pilot.press("S", "D")
        await pilot.pause()
        await pilot.press("S", "P")
        await pilot.pause()

        assert app.api.vars.todo_sort == "priority"
        assert visible_descriptions(tree) == ["gamma", "alpha", "beta"]


async def test_rows_nothing_orders_keep_their_filing():
    """A sort has nothing to say about rows without a date or priority"""

    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)

        for name in ("one", "two", "three"):
            await pilot.press("n")
            await commit_line(pilot, name)

        await pilot.press("S", "D")
        await pilot.pause()

        assert visible_descriptions(tree) == ["one", "two", "three"]


async def test_the_order_belongs_to_the_pane_not_the_project():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        await create_and_move_to_todo(pilot)
        await seed_unsorted(pilot)

        await pilot.press("S", "D")
        await pilot.pause()

        # A second project opened afterwards reads in the same order
        await new_project(pilot, "second")
        await pilot.press("ö", "n")
        await commit_line(pilot, "undated")
        await pilot.press("n")
        await commit_line(pilot, "dated")

        dated = next(t for t in Todo.all() if t.description == "dated")
        from datetime import datetime

        dated.due = datetime(2029, 1, 1)
        dated.save()

        from tests.test_ui.ui_base import visible_todos

        second_tree = visible_todos(app)
        second_tree.force_refresh()
        await pilot.pause()

        assert app.api.vars.todo_sort == "due"
        assert visible_descriptions(second_tree) == ["dated", "undated"]


async def test_fixed_projects_turn_the_sort_down():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        before = app.api.vars.todo_sort

        # The boot leaves the Today pane focused
        await pilot.press("S", "D")
        await pilot.pause()

        assert app.api.vars.todo_sort == before

        # Turned down with a word about why, not announced as a sort
        message = notification_message(app)
        assert message is not None and "can't be sorted" in message


async def test_the_cursor_stays_on_its_row_across_a_sort():
    async with run_pilot() as pilot:
        tree = await create_and_move_to_todo(pilot)
        await seed_unsorted(pilot)

        # The cursor sits on the last row typed in: gamma
        assert tree.current_model.description == "gamma"

        await pilot.press("S", "S")
        await pilot.pause()

        # gamma moved to the foot of the pane, and the cursor went with it
        assert tree.current_model.description == "gamma"
