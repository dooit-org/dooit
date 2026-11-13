from typing import List, Tuple
from datetime import datetime, timedelta
from pytest import raises, mark
from dooit.api.exceptions import NoParentError, MultipleParentError
from dooit.api import Todo, Workspace
from tests.test_core.core_base import *  # noqa


def _sort_before_and_after(session, field) -> Tuple[List[Todo], List[Todo]]:
    from tests.generate_test_data import generate

    generate(session)
    w = Workspace.all()[2]
    t = w.todos[0]
    old_todos = t.siblings
    t.sort_siblings(field)
    new_descriptions = t.siblings
    return old_todos, new_descriptions


def test_todo_creation(create_workspace, create_todo):
    w = create_workspace()
    _ = [create_todo(parent_workspace=w) for _ in range(5)]

    result = Todo.all()
    assert len(result) == 5

    indexs = sorted([t.order_index for t in result])
    assert indexs == [0, 1, 2, 3, 4]


def test_sibling_methods(create_workspace, create_todo):
    w = create_workspace()
    _ = [create_todo(parent_workspace=w) for _ in range(5)]

    todo = Todo.all()[0]
    assert todo is not None

    siblings = todo.siblings
    index_ids = [w.order_index for w in siblings]
    assert index_ids == [0, 1, 2, 3, 4]
    assert siblings[0].is_first_sibling()
    assert siblings[-1].is_last_sibling()


def test_todo_siblings_by_creation(create_workspace, create_todo):
    w = create_workspace()
    todo = [create_todo(parent_workspace=w) for _ in range(5)][0]
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


def test_with_both_parents(create_todo, create_workspace):
    with raises(MultipleParentError):
        create_todo(parent_workspace=create_workspace(), parent_todo=create_todo())


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
        "effort",
        "recurrence",
        "urgency",
        "pending",
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


def test_toggle_complete_parent(create_workspace, create_todo):
    w = create_workspace()
    t = w.add_todo()
    t1 = t.add_todo()
    t2 = t.add_todo()

    t1.toggle_complete()
    assert not t.is_completed

    t2.toggle_complete()
    assert t.is_completed

    t1.toggle_complete()
    assert not t.is_completed


def test_due_date_util(create_workspace, create_todo):
    w = create_workspace()
    t = w.add_todo()
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


def test_due_today_ignores_other_months(create_workspace):
    w = create_workspace()
    t = w.add_todo()
    now = datetime.now()

    t.due = now.replace(year=now.year + 1)
    assert not t.is_due_today()

    t.due = now.replace(hour=0, minute=0)
    assert t.is_due_today()


def test_tags(create_workspace, create_todo):
    w = create_workspace()
    t = w.add_todo()
    t.description = "This is a @tag"
    assert t.tags == ["@tag"]

    t.description = "This is a @tag and @another"
    assert t.tags == ["@tag", "@another"]

    t.description = "This is a tag"
    assert t.tags == []


def test_urgency(create_workspace, create_todo):
    w = create_workspace()
    t = w.add_todo()
    assert t.urgency == 1

    t.decrease_urgency()
    assert t.urgency == 1

    t.increase_urgency()
    t.increase_urgency()
    t.increase_urgency()
    t.increase_urgency()
    t.increase_urgency()
    assert t.urgency == 4


def test_recurrence_change(create_workspace, create_todo):
    w = create_workspace()
    t = w.add_todo()
    t.due = datetime.strptime("2021-01-01", "%Y-%m-%d")
    t.recurrence = timedelta(days=1)
    t.save()
    assert t.due == datetime.strptime("2021-01-01", "%Y-%m-%d")
    t.toggle_complete()
    assert t.due == datetime.strptime("2021-01-02", "%Y-%m-%d")


def test_recurrence_without_due_starts_one_period_away(create_workspace):
    w = create_workspace()
    t = w.add_todo()

    before = datetime.now()
    t.recurrence = timedelta(days=1)
    t.save()

    assert t.due >= before + timedelta(days=1)
    assert not t.is_overdue

    t.due = None
    t.toggle_complete()  # completing an undated occurrence
    assert t.pending
    assert t.due >= before + timedelta(days=1)


def test_recurrence_logs_completion(create_workspace):
    w = create_workspace()
    t = w.add_todo()
    t.due = datetime.strptime("2021-01-01", "%Y-%m-%d")
    t.recurrence = timedelta(days=1)
    t.save()

    t.toggle_complete()
    assert t.pending
    assert len(t.todos) == 1

    log = t.todos[0]
    assert log.is_completed
    assert log.recurrence is None
    assert log.description == f"Completed on {datetime.now():%Y-%m-%d}"

    t.toggle_complete()
    assert len(t.todos) == 2
    assert t.todos[0].id != log.id  # newest first
    assert t.todos[1].id == log.id

    # saving the recurring todo again keeps its history completed
    t.description = "renamed"
    t.save()
    assert all(child.is_completed for child in t.todos)


def test_finishing_subtasks_rolls_recurring_parent_over(session, create_workspace):
    w = create_workspace()
    p = w.add_todo()
    p.due = datetime(2030, 1, 1)
    p.recurrence = timedelta(days=7)
    p.save()
    step = p.add_todo()
    step.description = "step"
    step.save()

    step.toggle_complete()
    session.expire_all()

    assert p.pending
    assert p.due == datetime(2030, 1, 8)
    assert [t.is_completion_log for t in p.todos] == [True, False]


def test_completing_history_entry_does_not_roll_over(session, create_workspace):
    w = create_workspace()
    p = w.add_todo()
    p.due = datetime(2030, 1, 1)
    p.recurrence = timedelta(days=7)
    p.save()
    p.toggle_complete()

    log = p.todos[0]
    log.toggle_complete()  # reopen
    log.toggle_complete()  # and complete again
    session.expire_all()

    assert p.pending
    assert p.due == datetime(2030, 1, 8)
    assert len(p.todos) == 1


def test_non_recurring_completion_adds_no_child(create_workspace):
    w = create_workspace()
    t = w.add_todo()

    t.toggle_complete()
    assert t.is_completed
    assert t.todos == []


def test_clone_into_own_subtree(create_workspace):
    w = create_workspace()
    p = w.add_todo()
    p.description = "p"
    c = p.add_todo()
    c.description = "c"
    c.save()

    clone = Todo.clone_from_id(p.id, 0, parent=c)

    assert clone.parent_todo == c
    assert [t.description for t in c.todos] == ["p"]
    assert [t.description for t in clone.todos] == ["c"]
    assert clone.todos[0].todos == []


def test_clone_defaults_to_original_parent(create_workspace):
    w = create_workspace()
    p = w.add_todo()
    c = p.add_todo()

    clone = Todo.clone_from_id(c.id, 0)
    assert clone.parent_todo == p


def _order(parent):
    return [(t.description, t.order_index) for t in parent.todos]


def _add(parent, *names):
    for name in names:
        t = parent.add_todo()
        t.description = name
        t.save()


def test_insert_only_shifts_siblings(session, create_workspace):
    w1, w2 = create_workspace("w1"), create_workspace("w2")
    _add(w1, "a", "b")
    _add(w2, "x", "y", "z")

    sibling = w1.todos[0].add_sibling()
    sibling.description = "a2"
    sibling.save()
    _add(w1.todos[0], "child")
    session.expire_all()

    assert _order(w1) == [("a", 0), ("a2", 1), ("b", 2)]
    assert _order(w2) == [("x", 0), ("y", 1), ("z", 2)]
    assert _order(w1.todos[0]) == [("child", 0)]


def test_drop_renumbers_siblings(session, create_workspace):
    w = create_workspace()
    _add(w, "a", "b", "c")

    w.todos[1].drop()
    session.expire_all()
    assert _order(w) == [("a", 0), ("c", 1)]

    w.todos[1].shift_up()
    session.expire_all()
    assert _order(w) == [("c", 0), ("a", 1)]


def test_shift_repairs_gaps(session, create_workspace):
    w = create_workspace()
    _add(w, "a", "b", "c")
    for todo, index in zip(w.todos, [0, 4, 9]):
        todo.order_index = index
    session.commit()

    w.todos[2].shift_up()
    session.expire_all()
    assert _order(w) == [("a", 0), ("c", 1), ("b", 2)]

    w.todos[0].shift_down()
    session.expire_all()
    assert _order(w) == [("c", 0), ("a", 1), ("b", 2)]


def test_sort_invalid(create_workspace, create_todo):
    w = create_workspace()
    t = w.add_todo()
    with raises(AttributeError):
        t.sort_siblings("???????")


def test_sort_natural(create_workspace):
    w = create_workspace()

    def add(desc, urgency=1, due=None, pending=True):
        t = w.add_todo()
        t.description = desc
        t.urgency = urgency
        t.due = datetime.strptime(due, "%Y-%m-%d") if due else None
        t.pending = pending
        t.save()
        return t

    add("done urgent", urgency=4, pending=False)
    add("low no due")
    add("high late", urgency=3, due="2030-02-01")
    add("done low", pending=False)
    add("high soon", urgency=3, due="2030-01-01")
    add("low soon", due="2030-01-01")
    add("high no due", urgency=3)

    w.todos[0].sort_siblings("natural")

    assert [t.description for t in w.todos] == [
        "high soon",
        "high late",
        "high no due",
        "low soon",
        "low no due",
        "done urgent",
        "done low",
    ]


@mark.parametrize(
    "field,sort_key,filter_func,compare_ids",
    [
        (
            "natural",
            lambda x: (
                not x.pending,
                -x.urgency,
                x.due or datetime.max,
                x.order_index,
            ),
            None,
            True,
        ),
        (
            "pending",
            lambda x: (not x.pending, x.due or datetime.max, x.order_index),
            None,
            True,
        ),
        ("description", lambda x: x.description, None, False),
        ("recurrence", lambda x: x.recurrence, lambda x: x.recurrence, False),
        ("effort", lambda x: x.effort, None, False),
        ("urgency", lambda x: x.urgency, None, False),
        ("due", lambda x: x.due, lambda x: x.due, True),
    ],
)
def test_sort(session, create_workspace, field, sort_key, filter_func, compare_ids):
    old, new = _sort_before_and_after(session, field)

    if filter_func:
        old = [t for t in old if filter_func(t)]
        new = new[: len(old)]

    old.sort(key=sort_key)

    if compare_ids:
        assert [i.id for i in old] == [i.id for i in new]
    else:
        assert old == new


def test_clone_from_id(create_workspace, create_todo):
    # Create source todo with nested structure
    w = create_workspace("Test Workspace")
    t = w.add_todo()
    t.description = "Parent Todo"
    t.due = datetime.now()
    t.effort = 3
    t.urgency = 2
    t.save()

    # Add child todos
    child1 = t.add_todo()
    child1.description = "Child Todo 1"
    child1.save()

    child2 = t.add_todo()
    child2.description = "Child Todo 2"
    child2.save()

    # Add grandchild todo
    grandchild = child1.add_todo()
    grandchild.description = "Grandchild Todo"
    grandchild.save()

    # Clone the todo
    cloned_todo = Todo.clone_from_id(t.id, 10)

    # Check basic properties were copied
    assert cloned_todo.id != t.id
    assert cloned_todo.description == "Parent Todo"
    assert cloned_todo.due == t.due
    assert cloned_todo.effort == 3
    assert cloned_todo.urgency == 2
    assert cloned_todo.order_index == 10
    assert cloned_todo.parent_workspace_id == w.id

    # Check child todos were cloned
    assert len(cloned_todo.todos) == 2

    # Check grandchild todo was cloned
    child_descriptions = [child.description for child in cloned_todo.todos]
    assert "Child Todo 1" in child_descriptions
    assert "Child Todo 2" in child_descriptions

    # Find the cloned Child Todo 1
    cloned_child1 = next(
        child for child in cloned_todo.todos if child.description == "Child Todo 1"
    )

    # Check grandchild was cloned properly
    assert len(cloned_child1.todos) == 1
    assert cloned_child1.todos[0].description == "Grandchild Todo"
