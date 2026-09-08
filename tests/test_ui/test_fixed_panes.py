"""
The panes of the fixed projects: what they draw, and what they turn away
"""


from dooit.api import Todo
from tests.test_ui.ui_base import (
    boot,
    commit_line,
    create_and_move_to_todo,
    new_project,
    new_todo,
    notification_message,
    run_pilot,
    tree_options,
    visible_todos,
)


async def schedule(pilot, when: str):
    """Schedules the highlighted todo by typing into the `s` edit"""

    await pilot.press("s")
    await commit_line(pilot, when)


async def test_today_draws_a_block_per_project():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await new_project(pilot, "home")
        await new_todo(pilot, "water plants")
        await schedule(pilot, "today")

        await new_project(pilot, "work")
        await new_todo(pilot, "write report")
        await schedule(pilot, "today")

        await pilot.press("g", "t")
        await pilot.pause()

        tree = visible_todos(app)
        rows = tree_options(tree)
        assert len(rows) == 2

        # A heading per project stands over the rows (headings are furniture,
        # so they show up as static rows between the stored ones)
        headings = [
            _id
            for _id in (o.id for o in tree._options)
            if _id and _id.startswith("dooit-todo-group")
        ]
        assert len(headings) == 2


async def test_today_hides_the_scheduled_column():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "planned")
        await schedule(pilot, "today")

        await pilot.press("g", "t")
        await pilot.pause()

        today_tree = visible_todos(app)
        columns = [item.value for item in today_tree.render_layout]

        assert "scheduled" not in columns
        assert "scheduled" in today_tree.editable_columns


async def test_upcoming_groups_by_day():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "sooner")
        await schedule(pilot, "tomorrow")

        await pilot.press("n")
        await commit_line(pilot, "later")
        await schedule(pilot, "in 3 days")

        await pilot.press("g", "u")
        await pilot.pause()

        upcoming = visible_todos(app)
        rows = tree_options(upcoming)
        assert [upcoming._renderers[o.id].model.description for o in rows] == [
            "sooner",
            "later",
        ]


async def test_completing_a_task_moves_it_to_completed():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        tree = await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "done deal")

        await pilot.press("c")
        await pilot.pause()

        # Gone from its own pane
        assert tree_options(tree) == []

        await pilot.press("g", "c")
        await pilot.pause()

        completed = visible_todos(app)
        rows = tree_options(completed)
        assert len(rows) == 1
        assert completed.current_model.description == "done deal"


async def test_completed_holds_an_unticked_row():
    """Unticking in the log must not drop the row out from under the edit"""

    async with run_pilot() as pilot:
        app = await boot(pilot)

        tree = await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "not quite done")
        await pilot.press("c")
        await pilot.pause()

        await pilot.press("g", "c")
        await pilot.pause()

        completed = visible_todos(app)
        await pilot.press("c")  # untick it right there
        await pilot.pause()

        todo = Todo.all()[0]
        assert todo.is_pending

        # Still on screen in the log, held while it is being seen to
        assert len(tree_options(completed)) == 1

        # And back in its own project's pane at the same time
        assert len(tree_options(tree)) == 1


async def test_fixed_panes_refuse_reordering_and_adding():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "planned")
        await schedule(pilot, "today")

        await pilot.press("g", "t")
        await pilot.pause()

        for keys, refused in (
            (("n",), "added"),
            (("N",), "added"),
            (("K",), "reordered"),
            (("L",), "reordered"),
            (("I",), "reordered"),
            (("U",), "reordered"),
        ):
            await pilot.press(*keys)
            await pilot.pause()

            message = notification_message(app)
            assert message is not None and refused in message, keys

        assert len(Todo.all()) == 1


async def test_binning_from_today_removes_it_everywhere():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        tree = await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "planned")
        await schedule(pilot, "today")

        await pilot.press("g", "t")
        await pilot.pause()

        await pilot.press("x", "x")
        await pilot.pause()

        today_tree = visible_todos(app)
        assert tree_options(today_tree) == []
        assert tree_options(tree) == []

        todo = Todo.all()[0]
        assert todo.is_binned


async def test_binning_twice_warns_instead_of_stamping_again():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await new_project(pilot, "project")
        await new_todo(pilot, "doomed")

        await pilot.press("x", "x")
        await pilot.pause()

        await pilot.press("g", "b")
        await pilot.pause()

        await pilot.press("x", "x")
        await pilot.pause()

        message = notification_message(app)
        assert message is not None and "Already in the Bin" in message


async def test_restore_outside_the_bin_warns():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await new_project(pilot, "project")
        await new_todo(pilot, "still here")

        await pilot.press("u")
        await pilot.pause()

        message = notification_message(app)
        assert message is not None and "Bin" in message
        assert not Todo.all()[0].is_binned


async def test_restore_from_the_bin():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "second thoughts")

        await pilot.press("x", "x")
        await pilot.pause()

        await pilot.press("g", "b")
        await pilot.pause()

        bin_tree = visible_todos(app)
        assert len(tree_options(bin_tree)) == 1

        await pilot.press("u")
        await pilot.pause()

        assert tree_options(bin_tree) == []

        todo = Todo.all()[0]
        assert not todo.is_binned
        assert todo.parent_project is not None
        assert todo.parent_project.description == "project"


async def test_empty_bin_via_chord():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await create_and_move_to_todo(pilot)
        for name in ("one", "two"):
            await pilot.press("n")
            await commit_line(pilot, name)
            await pilot.press("x", "x")
            await pilot.pause()

        # From anywhere at all; the question counts what is about to go
        await pilot.press("Y", "Y")
        await pilot.pause()

        assert app.bar_switcher.current == "confirm_bar"
        assert "2 tasks" in app.bar_switcher.visible_content.message

        await pilot.press("y")
        await pilot.pause()

        assert Todo.all() == []


async def test_deleting_from_the_bin_leaves_no_ghost_row():
    """
    A todo deleted for good in the Bin must be gone from its old project's
    pane as well — a pane that keeps a row for it hands the cursor a model
    that is no longer in the database, and the next edit crashes.
    """

    async with run_pilot() as pilot:
        app = await boot(pilot)

        tree = await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "doomed")

        await pilot.press("x", "x")
        await pilot.pause()

        await pilot.press("g", "b")
        await pilot.pause()

        await pilot.press("y", "y")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()

        assert Todo.all() == []

        # Back on the project the todo was filed under
        await pilot.press("j")
        await pilot.pause()
        app.project_tree.highlight_id(tree.model.uuid)
        await pilot.pause()
        await pilot.press("ö")
        await pilot.pause()

        pane = visible_todos(app)
        assert tree_options(pane) == []
        assert pane.highlighted is None
