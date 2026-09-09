from typing import List, Tuple
from datetime import datetime, timedelta
from pytest import raises, mark
from dooit.api.exceptions import NoParentError, MultipleParentError
from dooit.api import Todo, Project
from tests.test_core.core_base import *  # noqa


def _sort_before_and_after(session, field) -> Tuple[List[Todo], List[Todo]]:
    from tests.generate_test_data import generate

    generate(session)
    p = Project.all()[2]
    t = p.todos[0]
    old_todos = t.siblings
    t.sort_siblings(field)
    new_descriptions = t.siblings
    return old_todos, new_descriptions


def test_todo_creation(create_project, create_todo):
    p = create_project()
    _ = [create_todo(parent_project=p) for _ in range(5)]

    result = Todo.all()
    assert len(result) == 5

    indexs = sorted([t.order_index for t in result])
    assert indexs == [0, 1, 2, 3, 4]


def test_sibling_methods(create_project, create_todo):
    p = create_project()
    _ = [create_todo(parent_project=p) for _ in range(5)]

    todo = Todo.all()[0]
    assert todo is not None

    siblings = todo.siblings
    index_ids = [p.order_index for p in siblings]
    assert index_ids == [0, 1, 2, 3, 4]
    assert siblings[0].is_first_sibling()
    assert siblings[-1].is_last_sibling()


def test_todo_siblings_by_creation(create_project, create_todo):
    p = create_project()
    todo = [create_todo(parent_project=p) for _ in range(5)][0]
    assert len(todo.siblings) == 5


def test_parent_kind(create_todo):
    todo1 = create_todo()
    assert not todo1.has_same_parent_kind

    todo2 = create_todo(parent_todo=todo1)
    assert todo2.has_same_parent_kind


def test_without_parent():
    t = Todo()

    with raises(NoParentError):
        t.save()


def test_with_both_parents(create_todo, create_project):
    with raises(MultipleParentError):
        create_todo(parent_project=create_project(), parent_todo=create_todo())


def test_sibling_add(create_todo):
    t = create_todo()

    t2 = t.add_sibling()
    assert len(t.siblings) == 2
    assert len(t2.siblings) == 2
    assert t2.order_index == 1


def test_comparable_fields():
    fields = Todo.comparable_fields()
    expected_fields = [
        "description",
        "due",
        "scheduled",
        "effort",
        "recurrence",
        "priority",
        "pending",
        "completed_at",
        "binned_at",
        "origin_path",
        "note",
    ]
    assert fields == expected_fields


def test_nest_level(create_todo):
    t = create_todo()
    assert t.nest_level == 0

    t = t.add_todo()
    assert t.nest_level == 1

    t = t.add_todo()
    assert t.nest_level == 2


def test_from_id(todo1):
    _id = todo1.id
    t_from_id = Todo.from_id(str(_id))
    assert t_from_id == todo1


def test_toggle_complete(todo1):
    assert todo1.pending
    assert todo1.is_pending
    assert not todo1.is_completed

    todo1.toggle_complete()
    assert not todo1.pending
    assert not todo1.is_pending
    assert todo1.is_completed


def test_toggle_complete_parent(create_project, create_todo):
    p = create_project()
    t = p.add_todo()
    t1 = t.add_todo()
    t2 = t.add_todo()

    t1.toggle_complete()
    assert not t.is_completed

    t2.toggle_complete()
    assert t.is_completed

    t1.toggle_complete()
    assert not t.is_completed


def test_due_date_util(create_project, create_todo):
    p = create_project()
    t = p.add_todo()
    assert not t.due
    assert not t.is_overdue
    assert not t.is_due_today()
    assert t.status == "pending"

    t.due = datetime.now()
    assert t.is_overdue
    assert t.due
    assert t.is_due_today()
    assert t.status == "overdue"

    t.due = datetime.now() - timedelta(days=1)
    assert not t.is_due_today()
    assert t.is_overdue
    assert t.status == "overdue"

    t.due = datetime.now() + timedelta(days=1)
    assert not t.is_overdue
    assert t.status == "pending"

    t.toggle_complete()
    assert t.status == "completed"


def test_tags(create_project, create_todo):
    p = create_project()
    t = p.add_todo()
    t.description = "This is a @tag"
    assert t.tags == ["@tag"]

    t.description = "This is a @tag and @another"
    assert t.tags == ["@tag", "@another"]

    t.description = "This is a tag"
    assert t.tags == []


def test_priority(create_project, create_todo):
    p = create_project()
    t = p.add_todo()
    assert t.priority == 0

    t.set_priority(1)
    assert t.priority == 1

    t.set_priority(3)
    assert t.priority == 3

    t.set_priority(-1)
    assert t.priority == 0

    t.set_priority(9)
    assert t.priority == 3


def test_recurrence_change(create_project, create_todo):
    p = create_project()
    t = p.add_todo()
    t.scheduled = datetime.strptime("2021-01-01", "%Y-%m-%d")
    t.recurrence = timedelta(days=1)
    t.save()
    assert t.scheduled == datetime.strptime("2021-01-01", "%Y-%m-%d")
    t.toggle_complete()
    assert t.scheduled == datetime.strptime("2021-01-02", "%Y-%m-%d")
    assert t.is_pending


def test_recurrence_takes_over_the_due_date(create_project):
    """A deadline becomes the first occurrence, and the column stays clear"""

    p = create_project()
    t = p.add_todo()
    t.due = datetime.strptime("2021-01-01", "%Y-%m-%d")
    t.recurrence = timedelta(weeks=1)
    t.save()

    assert t.due is None
    assert t.scheduled == datetime.strptime("2021-01-01", "%Y-%m-%d")


def test_recurrence_drops_a_due_date_it_cannot_use(create_project):
    """With a day already planned, the deadline is simply dropped"""

    p = create_project()
    t = p.add_todo()
    t.due = datetime.strptime("2021-01-01", "%Y-%m-%d")
    t.scheduled = datetime.strptime("2021-02-01", "%Y-%m-%d")
    t.recurrence = timedelta(weeks=1)
    t.save()

    assert t.due is None
    assert t.scheduled == datetime.strptime("2021-02-01", "%Y-%m-%d")


def test_sort_invalid(create_project, create_todo):
    p = create_project()
    t = p.add_todo()
    with raises(AttributeError):
        t.sort_siblings("???????")


@mark.parametrize(
    "field,sort_key,filter_func,compare_ids",
    [
        (
            "pending",
            lambda x: (not x.pending, x.due or datetime.max, x.order_index),
            None,
            True,
        ),
        ("description", lambda x: x.description, None, False),
        ("recurrence", lambda x: x.recurrence, lambda x: x.recurrence, False),
        ("effort", lambda x: x.effort, None, False),
        ("priority", lambda x: x.priority, None, False),
        ("due", lambda x: x.due, lambda x: x.due, True),
    ],
)
def test_sort(session, create_project, field, sort_key, filter_func, compare_ids):
    old, new = _sort_before_and_after(session, field)

    if filter_func:
        old = [t for t in old if filter_func(t)]
        new = new[: len(old)]

    old.sort(key=sort_key)

    if compare_ids:
        assert [i.id for i in old] == [i.id for i in new]
    else:
        assert old == new

# ------------------------------------------------------------------
# Behaviour this fork added to the model itself
# ------------------------------------------------------------------


def test_completion_is_stamped(create_project):
    p = create_project()
    t = p.add_todo()
    assert t.completed_at is None

    t.toggle_complete()
    assert t.completed_at is not None

    t.toggle_complete()
    assert t.completed_at is None


def test_effort_is_clamped(create_project):
    p = create_project()
    t = p.add_todo()

    t.set_effort(2)
    assert t.effort == 2

    t.set_effort(99)
    assert t.effort == 3

    t.set_effort(-5)
    assert t.effort == 0


def test_descendants(create_project):
    p = create_project()
    t = p.add_todo()
    child = t.add_todo()
    grandchild = child.add_todo()
    other = p.add_todo()

    assert t.descendants == [child, grandchild]
    assert other.descendants == []


def test_total_children_counts_only_open_work(create_project):
    """The count trailing a description is the work left, not the row count"""

    p = create_project()
    t = p.add_todo()

    child1 = t.add_todo()
    child1.description = "open step"
    child1.save()

    child2 = t.add_todo()
    child2.description = "done step"
    child2.save()

    grandchild = child1.add_todo()
    grandchild.description = "nested step"
    grandchild.save()

    assert t.total_children == 3

    child2.toggle_complete()
    assert t.total_children == 2

    from dooit.api import move_todo_to_bin

    move_todo_to_bin(child1)
    assert t.total_children == 0


def test_indent_files_under_previous_sibling(create_project):
    p = create_project()
    first = p.add_todo()
    first.description = "first"
    first.save()

    second = p.add_todo()
    second.description = "second"
    second.save()

    parent = second.indent()
    assert parent == first
    assert second.parent_todo == first
    assert second.parent_project is None
    assert first.todos == [second]


def test_indent_carries_steps_along(create_project):
    p = create_project()
    first = p.add_todo()
    second = p.add_todo()
    step = second.add_todo()

    second.indent()
    assert second.parent_todo == first
    assert step.parent_todo == second


def test_indent_with_nothing_above(create_project):
    p = create_project()
    only = p.add_todo()

    assert only.indent() is None
    assert only.parent_project == p


def test_unindent_lands_beside_the_old_parent(create_project):
    # A step on its way out to a project is briefly attached to neither, which
    # a `delete-orphan` cascade on `Todo.todos` used to read as a step nobody
    # wanted: it deleted the row instead of moving it, every sixth `U` or so
    p = create_project()
    first = p.add_todo()
    first.description = "first"
    first.save()

    last = p.add_todo()
    last.description = "last"
    last.save()

    step = first.add_todo()
    step.description = "step"
    step.save()

    grandparent = step.unindent()
    assert grandparent == p
    assert step.parent_project == p
    assert step.parent_todo is None

    # Directly under the task it was a step of, not at the end of the run
    ordered = sorted(p.todos, key=lambda t: t.order_index)
    assert [t.description for t in ordered] == ["first", "step", "last"]


def test_unindent_of_a_nested_step(create_project):
    p = create_project()
    task = p.add_todo()
    step = task.add_todo()
    sub_step = step.add_todo()

    assert sub_step.unindent() == task
    assert sub_step.parent_todo == task


def test_unindent_at_top_level(create_project):
    p = create_project()
    t = p.add_todo()

    assert t.unindent() is None
    assert t.parent_project == p


def test_tags_ignore_emails(create_project):
    p = create_project()
    t = p.add_todo()
    t.description = "mail bob@example.com about @work"

    assert t.tags == ["@work"]


def test_is_binned(create_project):
    from dooit.api import move_todo_to_bin

    p = create_project()
    t = p.add_todo()
    assert not t.is_binned

    move_todo_to_bin(t)
    assert t.is_binned
    assert t.binned_at is not None
