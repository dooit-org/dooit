"""
The fixed projects: Today, Upcoming, Completed and the Bin

What each one gathers, the blocks it gathers it into, and the order the
blocks and their rows come in.
"""

from datetime import datetime, timedelta

from dooit.api import (
    BIN,
    COMPLETED,
    TODAY,
    UPCOMING,
    move_todo_to_bin,
)
from dooit.api.fixed_projects import (
    PATH_SEPARATOR,
    fixed_project_from_id,
    fixed_project_from_key,
    fixed_projects,
    owning_project,
    project_path,
)
from tests.test_core.core_base import *  # noqa


def today_at(hour: int = 10) -> datetime:
    return datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)


# ------------------------------------------------------------------
# The registry and the helpers around it
# ------------------------------------------------------------------


def test_the_four_fixed_projects_are_registered():
    assert [p.key for p in fixed_projects()] == [
        "today",
        "upcoming",
        "completed",
        "bin",
    ]


def test_fixed_project_lookups(create_project):
    assert fixed_project_from_key("today") is TODAY
    assert fixed_project_from_key("nope") is None

    assert fixed_project_from_id(TODAY.uuid) is TODAY
    assert fixed_project_from_id("Todo_1") is None
    assert fixed_project_from_id(create_project().uuid) is None


def test_fixed_projects_cannot_be_mistaken_for_stored_ones():
    assert TODAY.is_fixed
    assert COMPLETED.pinned_bottom and BIN.pinned_bottom
    assert COMPLETED.muted and BIN.muted
    assert not TODAY.pinned_bottom


def test_owning_project(create_project):
    p = create_project("home")
    task = p.add_todo()
    step = task.add_todo()
    sub_step = step.add_todo()

    assert owning_project(task) == p
    assert owning_project(sub_step) == p


def test_project_path(create_project):
    outer = create_project("outer")
    inner = Project(description="inner", parent_project=outer)  # noqa: F405
    inner.save()

    assert project_path(outer) == "outer"
    assert project_path(inner) == f"outer{PATH_SEPARATOR}inner"


# ------------------------------------------------------------------
# Today
# ------------------------------------------------------------------


def test_today_gathers_what_is_scheduled_today(create_project):
    p = create_project("work")

    scheduled = p.add_todo()
    scheduled.description = "today's work"
    scheduled.scheduled = today_at()
    scheduled.save()

    unscheduled = p.add_todo()
    unscheduled.description = "someday"
    unscheduled.save()

    ahead = p.add_todo()
    ahead.scheduled = today_at() + timedelta(days=2)
    ahead.save()

    assert TODAY.todos == [scheduled]


def test_today_leaves_out_finished_and_binned_work(create_project):
    p = create_project("work")

    done = p.add_todo()
    done.scheduled = today_at()
    done.save()
    done.toggle_complete()

    thrown = p.add_todo()
    thrown.scheduled = today_at()
    thrown.save()
    move_todo_to_bin(thrown)

    assert TODAY.todos == []


def test_today_groups_by_project_in_pane_order(create_project):
    first = create_project("first")
    second = create_project("second")

    t2 = second.add_todo()
    t2.scheduled = today_at()
    t2.save()

    t1 = first.add_todo()
    t1.scheduled = today_at()
    t1.save()

    groups = TODAY.todo_groups
    assert [g.label for g in groups] == ["first", "second"]
    assert groups[0].todos == [t1]
    assert groups[1].todos == [t2]


def test_today_orders_a_block_by_priority(create_project):
    p = create_project("work")

    low = p.add_todo()
    low.scheduled = today_at()
    low.priority = 3
    low.save()

    none = p.add_todo()
    none.scheduled = today_at()
    none.save()

    high = p.add_todo()
    high.scheduled = today_at()
    high.priority = 1
    high.save()

    (group,) = TODAY.todo_groups
    assert group.todos == [high, low, none]


def test_today_headings_carry_the_project_path(create_project):
    outer = create_project("outer")
    inner = Project(description="inner", parent_project=outer)  # noqa: F405
    inner.save()

    t = inner.add_todo()
    t.scheduled = today_at()
    t.save()

    (group,) = TODAY.todo_groups
    assert group.label == f"outer{PATH_SEPARATOR}inner"


# ------------------------------------------------------------------
# Upcoming
# ------------------------------------------------------------------


def test_upcoming_gathers_the_days_ahead_in_order(create_project):
    p = create_project("work")

    later = p.add_todo()
    later.scheduled = today_at() + timedelta(days=5)
    later.save()

    soon = p.add_todo()
    soon.scheduled = today_at() + timedelta(days=2)
    soon.save()

    today = p.add_todo()
    today.scheduled = today_at()
    today.save()

    groups = UPCOMING.todo_groups
    assert [g.todos for g in groups] == [[soon], [later]]
    assert today not in UPCOMING.todos


def test_upcoming_names_tomorrow(create_project):
    p = create_project("work")

    t = p.add_todo()
    t.scheduled = today_at() + timedelta(days=1)
    t.save()

    (group,) = UPCOMING.todo_groups
    assert group.label == "Tomorrow"


# ------------------------------------------------------------------
# Completed
# ------------------------------------------------------------------


def test_completed_is_a_log_of_finished_tasks(create_project):
    p = create_project("work")

    first_done = p.add_todo()
    first_done.toggle_complete()
    first_done.completed_at = datetime.now() - timedelta(hours=2)
    first_done.save()

    last_done = p.add_todo()
    last_done.toggle_complete()

    still_open = p.add_todo()
    still_open.save()

    # The most recently finished first, and nothing that is still open
    assert COMPLETED.todos == [last_done, first_done]


def test_completed_shows_whole_tasks_not_steps(create_project):
    """A finished step of an unfinished task has gone nowhere"""

    p = create_project("work")
    task = p.add_todo()
    step = task.add_todo()
    task.add_todo()

    step.toggle_complete()

    assert COMPLETED.todos == []

    # Only once the whole task is done does it arrive, as the task
    for child in task.todos:
        if child.is_pending:
            child.toggle_complete()

    assert COMPLETED.todos == [task]


def test_completed_leaves_out_the_binned(create_project):
    p = create_project("work")
    t = p.add_todo()
    t.toggle_complete()
    move_todo_to_bin(t)

    assert COMPLETED.todos == []


# ------------------------------------------------------------------
# Bin
# ------------------------------------------------------------------


def test_bin_is_a_log_of_thrown_away_tasks(create_project):
    p = create_project("work")

    first_out = p.add_todo()
    move_todo_to_bin(first_out)
    first_out.binned_at = datetime.now() - timedelta(hours=2)
    first_out.save()

    last_out = p.add_todo()
    move_todo_to_bin(last_out)

    kept = p.add_todo()
    kept.save()

    assert BIN.todos == [last_out, first_out]
    assert kept not in BIN.todos


def test_bin_shows_a_task_with_its_steps_inside_it(create_project):
    p = create_project("work")
    task = p.add_todo()
    task.add_todo()

    move_todo_to_bin(task)

    # One row: the task. The step is drawn under it, not beside it.
    assert BIN.todos == [task]
