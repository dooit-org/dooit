"""
The Bin: throwing work away, getting it back, and emptying it out
"""

from dooit.api import (
    Project,
    Todo,
    binned_tasks,
    empty_bin,
    move_project_to_bin,
    move_todo_to_bin,
    restore_todo,
)
from dooit.api.recycle import REVIVED_PREFIX, UNKNOWN_PROJECT, revive_home
from tests.test_core.core_base import *  # noqa


def test_binning_stamps_the_whole_family(create_project):
    p = create_project()
    task = p.add_todo()
    step = task.add_todo()
    sub_step = step.add_todo()

    move_todo_to_bin(task)

    assert task.is_binned
    assert step.is_binned
    assert sub_step.is_binned

    # One stamp over the family, so the Bin keeps them together
    assert task.binned_at == step.binned_at == sub_step.binned_at


def test_binned_tasks_counts_tasks_not_rows(create_project):
    """A step inside a binned task is part of it, not a task of its own"""

    p = create_project()
    task = p.add_todo()
    task.add_todo()
    other = p.add_todo()

    move_todo_to_bin(task)
    move_todo_to_bin(other)

    tasks = binned_tasks()
    assert len(tasks) == 2
    assert task in tasks
    assert other in tasks


def test_a_step_binned_on_its_own_is_a_task_of_its_own(create_project):
    p = create_project()
    task = p.add_todo()
    step = task.add_todo()

    move_todo_to_bin(step)

    assert not task.is_binned
    assert binned_tasks() == [step]


def test_restore_takes_the_family_back_out(create_project):
    p = create_project()
    task = p.add_todo()
    step = task.add_todo()

    move_todo_to_bin(task)
    restore_todo(task)

    assert not task.is_binned
    assert not step.is_binned
    assert task.parent_project == p
    assert binned_tasks() == []


def test_dropping_a_project_keeps_its_work(create_project):
    """The project row is the only thing that actually goes"""

    p = create_project("home")
    t1 = p.add_todo()
    t1.description = "water plants"
    t1.save()
    t2 = p.add_todo()
    t2.description = "fix door"
    t2.save()

    move_project_to_bin(p)

    assert Project.all() == []

    todos = Todo.all()
    assert len(todos) == 2
    assert all(t.is_binned for t in todos)
    assert all(t.is_orphan for t in todos)
    assert all(t.origin_path == "home" for t in todos)


def test_dropping_a_project_takes_nested_projects_along(create_project):
    p = create_project("outer")
    inner = Project(description="inner", parent_project=p)
    inner.save()

    t = inner.add_todo()
    t.description = "nested work"
    t.save()

    move_project_to_bin(p)

    assert Project.all() == []
    assert t.is_binned
    # The path names every project it was filed down through
    assert "outer" in t.origin_path and "inner" in t.origin_path


def test_restoring_rebuilds_the_project_it_came_from(create_project):
    p = create_project("home")
    t = p.add_todo()
    t.description = "water plants"
    t.save()

    move_project_to_bin(p)
    created = restore_todo(t)

    assert not t.is_binned
    assert not t.is_orphan
    assert len(created) == 1
    assert created[0].description == f"{REVIVED_PREFIX}home"
    assert t.parent_project == created[0]
    assert t.origin_path == ""


def test_restoring_into_a_project_that_still_exists(create_project):
    """A project that is still there takes the todo straight back"""

    p = create_project("home")
    t = p.add_todo()
    t.save()

    move_todo_to_bin(t)
    created = restore_todo(t)

    assert created == []
    assert t.parent_project == p


def test_second_revival_joins_the_first(create_project):
    """Two todos out of the same dead project end up back together"""

    p = create_project("home")
    t1 = p.add_todo()
    t2 = p.add_todo()

    move_project_to_bin(p)

    first_created = restore_todo(t1)
    second_created = restore_todo(t2)

    assert len(first_created) == 1
    assert second_created == []
    assert t1.parent_project == t2.parent_project


def test_reviving_without_a_path(create_project):
    """Something has to be there to put it in"""

    p = create_project("home")
    t = p.add_todo()
    move_project_to_bin(p)

    # A path that names nothing: the todo still has somewhere to come from,
    # but nothing to rebuild out of it
    t.origin_path = " "
    created = revive_home(t)

    assert len(created) == 1
    assert created[0].description == f"{REVIVED_PREFIX}{UNKNOWN_PROJECT}"
    assert t.parent_project == created[0]


def test_restoring_a_finished_orphan_leaves_it_in_the_log(create_project):
    """A done todo has the completion log to live in; nothing is rebuilt"""

    p = create_project("home")
    t = p.add_todo()
    t.toggle_complete()

    move_project_to_bin(p)
    created = restore_todo(t)

    assert created == []
    assert not t.is_binned
    assert t.is_orphan


def test_empty_bin_deletes_for_good(create_project):
    p = create_project()
    task = p.add_todo()
    step = task.add_todo()
    kept = p.add_todo()

    task_uuid, step_uuid = task.uuid, step.uuid

    move_todo_to_bin(task)
    gone = empty_bin()

    # Every row that went, steps included, so panes can forget them
    assert sorted(gone) == sorted([task_uuid, step_uuid])

    assert binned_tasks() == []
    assert Todo.all() == [kept]


def test_empty_bin_with_nothing_in_it(create_project):
    create_project()
    assert empty_bin() == []
