from datetime import datetime, timedelta

from tests.test_core.core_base import *  # noqa


def test_todo_status_update_children(todo1):
    assert todo1.is_pending

    for child_todo in todo1.todos:
        child_todo.toggle_complete()

    assert not todo1.is_pending


def test_ticking_the_last_step_ticks_the_whole_chain(create_project):
    """Finishing the final step of the final part finishes the whole task"""

    p = create_project()
    task = p.add_todo()
    part = task.add_todo()
    step1 = part.add_todo()
    step2 = part.add_todo()

    step1.toggle_complete()
    assert part.is_pending
    assert task.is_pending

    step2.toggle_complete()
    assert part.is_completed
    assert task.is_completed


def test_ticking_a_parent_ticks_everything_underneath(create_project):
    p = create_project()
    task = p.add_todo()
    step = task.add_todo()
    sub_step = step.add_todo()

    task.toggle_complete()

    assert step.is_completed
    assert sub_step.is_completed


def test_family_shares_one_completion_stamp(create_project):
    """The moment the last step was done is the moment the task was done"""

    p = create_project()
    task = p.add_todo()
    step = task.add_todo()

    task.toggle_complete()

    assert task.completed_at is not None
    assert step.completed_at == task.completed_at


def test_unticking_a_step_unticks_every_ancestor(create_project):
    p = create_project()
    task = p.add_todo()
    part = task.add_todo()
    step = part.add_todo()

    task.toggle_complete()
    assert task.is_completed

    step.toggle_complete()

    assert step.is_pending
    assert part.is_pending
    assert task.is_pending


def test_unticking_a_task_unticks_its_steps(create_project):
    """A task is undone the moment any part of it is"""

    p = create_project()
    task = p.add_todo()
    step1 = task.add_todo()
    step2 = task.add_todo()

    task.toggle_complete()
    assert step1.is_completed and step2.is_completed

    task.toggle_complete()

    assert step1.is_pending
    assert step2.is_pending


def test_unticking_leaves_finished_siblings_alone(create_project):
    """Unticking one step does not undo the work beside it"""

    p = create_project()
    task = p.add_todo()
    step1 = task.add_todo()
    step2 = task.add_todo()

    step1.toggle_complete()
    step2.toggle_complete()
    assert task.is_completed

    step1.toggle_complete()

    assert task.is_pending
    assert step2.is_completed


def test_recurrence_forces_pending(create_project):
    """Setting a recurrence on a finished todo hands it back as work"""

    p = create_project()
    t = p.add_todo()
    t.toggle_complete()
    assert t.is_completed

    t.recurrence = timedelta(days=7)
    t.save()

    assert t.is_pending


def test_completing_recurring_todo_bounces_it_forward(create_project):
    p = create_project()
    t = p.add_todo()
    t.scheduled = datetime(2026, 1, 1)
    t.recurrence = timedelta(days=3)
    t.save()

    t.toggle_complete()

    assert t.is_pending
    assert t.scheduled == datetime(2026, 1, 4)
    assert t.completed_at is None


def test_completing_recurring_todo_without_a_date_schedules_it(create_project):
    """A recurring todo with no day planned starts counting from now"""

    p = create_project()
    t = p.add_todo()
    t.recurrence = timedelta(days=1)
    t.save()

    before = datetime.now()
    t.toggle_complete()

    assert t.is_pending
    assert t.scheduled is not None
    assert t.scheduled >= before
