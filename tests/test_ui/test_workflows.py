"""
Combined workflows: several features exercised in one sitting, the way a day
of real use strings them together
"""

from datetime import date, timedelta

from dooit.api import BIN, COMPLETED, TODAY, UPCOMING, Project, Todo
from dooit.ui.screens.search import SearchScreen
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


async def test_a_task_s_whole_life():
    """
    Create, describe, prioritize, size, date, annotate, finish: every column
    of a row touched once, and the row ends up in the completion log.
    """

    async with run_pilot() as pilot:
        await boot(pilot)

        tree = await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "ship the release")

        await pilot.press("p", "1")
        await pilot.press("e", "3")
        await pilot.press("d")
        await commit_line(pilot, "in 3 days")
        await pilot.press("s")
        await commit_line(pilot, "tomorrow")
        await pilot.pause()

        await pilot.press(" ")
        await pilot.pause()
        await pilot.press("i")
        await pilot.press(*list("remember the changelog"))
        await pilot.press("escape", "escape")
        await pilot.pause()

        todo = Todo.all()[0]
        assert todo.description == "ship the release"
        assert todo.priority == 1
        assert todo.effort == 3
        assert todo.due is not None and todo.due.date() == date.today() + timedelta(days=3)
        assert todo.scheduled is not None
        assert todo.scheduled.date() == date.today() + timedelta(days=1)
        assert todo.note == "remember the changelog"

        # Finish it: the row leaves the project pane for the log
        await pilot.press("c")
        await pilot.pause()

        assert todo.is_completed
        assert tree_options(tree) == []
        assert COMPLETED.todos == [todo]

        # And unticking it in the log hands it back
        await pilot.press("g", "c")
        await pilot.pause()
        await pilot.press("c")
        await pilot.pause()

        assert todo.is_pending
        assert len(tree_options(tree)) == 1


async def test_planning_a_day_across_projects():
    """
    Two projects, three scheduled tasks: Today gathers this day's two into a
    block per project, Upcoming holds the third, and finishing one from the
    Today pane empties its block.
    """

    async with run_pilot() as pilot:
        app = await boot(pilot)

        await new_project(pilot, "home")
        await new_todo(pilot, "water plants")
        await pilot.press("s")
        await commit_line(pilot, "today")

        await new_project(pilot, "work")
        await new_todo(pilot, "write report")
        await pilot.press("s")
        await commit_line(pilot, "today")
        await pilot.press("n")
        await commit_line(pilot, "plan sprint")
        await pilot.press("s")
        await commit_line(pilot, "tomorrow")

        assert len(TODAY.todos) == 2
        assert [t.description for t in TODAY.todos] == [
            "water plants",
            "write report",
        ]
        assert [t.description for t in UPCOMING.todos] == ["plan sprint"]

        # Work the day off its own pane
        await pilot.press("g", "t")
        await pilot.pause()

        today_tree = visible_todos(app)
        assert today_tree.current_model.description == "water plants"

        await pilot.press("c")
        await pilot.pause()

        assert len(TODAY.todos) == 1
        assert len(tree_options(today_tree)) == 1


async def test_steps_of_a_task_finish_the_task():
    """
    Steps added with N, finished one by one from the pane: the parent ticks
    itself the moment the last one is done, and the whole family shows in
    the log together.
    """

    async with run_pilot() as pilot:
        app = await boot(pilot)

        tree = await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "move house")

        await pilot.press("N")
        await commit_line(pilot, "pack boxes")
        await pilot.press("n")
        await commit_line(pilot, "book van")

        parent = next(t for t in Todo.all() if t.description == "move house")
        assert len(tree_options(tree)) == 3  # parent expanded, both steps

        # Finish the steps; the cursor sits on "book van"
        await pilot.press("c")
        await pilot.pause()
        assert parent.is_pending

        await pilot.press("k")  # up to "pack boxes"
        await pilot.press("c")
        await pilot.pause()

        assert parent.is_completed

        # The whole family left the project pane together
        assert tree_options(tree) == []
        assert COMPLETED.todos == [parent]

        # Unticking one step in the log hands the whole task back
        await pilot.press("g", "c")
        await pilot.pause()

        completed_tree = visible_todos(app)
        rows = tree_options(completed_tree)

        # The task with its steps under it
        assert len(rows) == 3

        await pilot.press("l")  # down onto a step
        await pilot.press("c")
        await pilot.pause()

        assert parent.is_pending
        assert len(tree_options(tree)) >= 1


async def test_bin_round_trip_with_a_dropped_project():
    """
    A project thrown away, its work restored from the Bin: the project comes
    back rebuilt under the revived name, and the Bin ends up empty.
    """

    async with run_pilot() as pilot:
        app = await boot(pilot)

        await new_project(pilot, "abandoned")
        await new_todo(pilot, "worth keeping")
        await new_todo(pilot, "worth losing")

        # Drop the whole project
        await pilot.press("j")
        await pilot.press("x", "x")
        await pilot.pause()

        assert Project.all() == []
        assert len(BIN.todos) == 2

        # Restore one task from the Bin
        await pilot.press("g", "b")
        await pilot.pause()

        bin_tree = visible_todos(app)

        # The Bin reads newest first; walk to "worth keeping"
        keeper = next(t for t in BIN.todos if t.description == "worth keeping")
        bin_tree.highlight_id(keeper.uuid)
        await pilot.press("u")
        await pilot.pause()

        revived = next(iter(Project.all()), None)
        assert revived is not None
        assert revived.description == "revived - abandoned"
        assert keeper.parent_project == revived

        message = notification_message(app)
        assert message is not None and "abandoned" in message

        # Empty the rest of the Bin for good
        await pilot.press("Y", "Y")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()

        assert BIN.todos == []
        assert [t.description for t in Todo.all()] == ["worth keeping"]


async def test_quick_add_then_find_it():
    """
    A task quick-added into a brand new project, then found again with the
    finder and jumped to.
    """

    async with run_pilot() as pilot:
        app = await boot(pilot)
        await new_project(pilot, "inbox")

        await pilot.press("C")
        await pilot.pause()
        await pilot.press(*list("research flights #travel tomorrow"))
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("y")  # yes, build "travel"
        await pilot.pause()

        travel = next(p for p in Project.all() if p.description == "travel")
        (todo,) = Todo.all()
        assert todo.parent_project == travel

        # Now find it from somewhere else entirely
        await pilot.press("g", "t")
        await pilot.pause()

        await pilot.press("/")
        await pilot.pause()
        assert isinstance(app.screen, SearchScreen)

        await pilot.press(*list("flights"))
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.pause()

        tree = visible_todos(app)
        assert tree.model.uuid == travel.uuid
        assert tree.current_model.description == "research flights"
        assert app.focused is tree


async def test_a_recurring_chore_through_the_day():
    """
    A chore scheduled today with a recurrence: Today shows it, ticking it
    bounces it to tomorrow, and Upcoming picks it up instead.
    """

    async with run_pilot() as pilot:
        await boot(pilot)

        await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "take out the bins")
        await pilot.press("s")
        await commit_line(pilot, "today")
        await pilot.press("r")
        await commit_line(pilot, "1d")

        todo = Todo.all()[0]
        assert todo.recurrence == timedelta(days=1)
        assert TODAY.todos == [todo]

        await pilot.press("g", "t")
        await pilot.pause()

        await pilot.press("c")
        await pilot.pause()

        # Never finished, only done for now
        assert todo.is_pending
        assert TODAY.todos == []

        from dooit.api import UPCOMING

        assert UPCOMING.todos == [todo]


async def test_indenting_builds_a_task_out_of_rows():
    """
    Two flat rows filed as task and step with I, shifted, and pulled apart
    again with U — the pane redrawn correctly at every step.
    """

    async with run_pilot() as pilot:
        app = await boot(pilot)

        tree = await create_and_move_to_todo(pilot)
        await pilot.press("n")
        await commit_line(pilot, "task")
        await pilot.press("n")
        await commit_line(pilot, "step")

        # Make "step" a step of "task"; the parent opens to show it
        await pilot.press("I")
        await pilot.pause()

        step = next(t for t in Todo.all() if t.description == "step")
        task = next(t for t in Todo.all() if t.description == "task")
        assert step.parent_todo == task
        assert len(tree_options(tree)) == 2

        # The child count rides along with the parent's description
        formatted = app.api.formatter.todos.description.format_value(
            task.description, task
        ).plain
        assert "(1)" in formatted

        # Pull it back out
        await pilot.press("U")
        await pilot.pause()

        assert step.parent_todo is None
        assert step.parent_project is not None
