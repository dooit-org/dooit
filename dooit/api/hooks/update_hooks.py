from datetime import datetime
from typing import Iterator, List
from sqlalchemy import event, update
from ..todo import Todo


def _descendants(todo: Todo) -> Iterator[Todo]:
    """
    Every todo filed under this one, at any depth
    """

    for child in todo.todos:
        yield child
        yield from _descendants(child)


def _ancestors(todo: Todo) -> Iterator[Todo]:
    """
    The todo this one hangs off, the one that hangs off, and so on up
    """

    node = todo.parent_todo

    while node is not None:
        yield node
        node = node.parent_todo


def _set_pending(connection, todos: List[Todo]) -> None:
    ids = [todo.id for todo in todos]

    if not ids:
        return

    query = (
        update(Todo)
        .where(Todo.id.in_(ids))
        .values(pending=True, completed_at=None)
    )
    connection.execute(query)


def _set_completed(connection, todos: List[Todo], stamp: datetime) -> None:
    ids = [todo.id for todo in todos]

    if not ids:
        return

    query = (
        update(Todo)
        .where(Todo.id.in_(ids))
        .values(pending=False, completed_at=stamp)
    )
    connection.execute(query)


@event.listens_for(Todo, "before_update")
def update_children_to_pending(_, connection, target: Todo):
    """
    Unticking a todo unticks everything underneath it

    The whole subtree at once rather than one level of it: what is done is the
    task, and a task is undone the moment any part of it is.
    """

    if not target.pending:
        return

    if any(todo.pending for todo in target.todos):
        return

    _set_pending(connection, list(_descendants(target)))


@event.listens_for(Todo, "before_update")
def update_children_to_completed(_, connection, target: Todo):
    """
    Ticking a todo ticks everything underneath it, at every depth
    """

    if target.pending:
        return

    stamp = target.completed_at or datetime.now()
    _set_completed(connection, list(_descendants(target)), stamp)


@event.listens_for(Todo, "before_update")
def update_parent_to_pending(mapper, connection, target: Todo):
    """
    Unticking a todo unticks every todo it is filed under

    All the way up rather than one level: a task with anything left to do in
    it is not finished, however deep in it that thing sits.
    """

    if not target.pending or not target.parent_todo:
        return

    _set_pending(connection, list(_ancestors(target)))


@event.listens_for(Todo, "before_update")
def update_parent_to_completed(mapper, connection, target: Todo):
    """
    Ticking off the last of a todo's children ticks the todo itself

    Carried on up for as long as it keeps being the last one: finishing the
    final step of the final part of something finishes the whole of it, and
    the whole of it is stamped with the moment that step was done.
    """

    if target.pending or not target.parent_todo:
        return

    stamp = target.completed_at or datetime.now()

    # The rows written here are only written straight to the database, so the
    # ones already dealt with still read as pending in the session: they are
    # kept track of rather than read back
    completed = {target.id}

    for node in _ancestors(target):
        if any(
            child.pending and child.id not in completed for child in node.todos
        ):
            break

        _set_completed(connection, [node], stamp)
        completed.add(node.id)


@event.listens_for(Todo, "before_insert")
@event.listens_for(Todo, "before_update")
def clear_due_for_recurrence(mapper, connection, todo: Todo):
    """
    A recurring todo carries no deadline, only the day it next comes round

    Nothing that repeats is owed by a date: what it has is the next time it is
    meant to be done, which is what `scheduled` holds. A deadline it was
    carrying before the recurrence was set becomes that first occurrence,
    unless a day was already planned for it, in which case it is dropped.
    """

    if todo.recurrence is None or todo.due is None:
        return

    if todo.scheduled is None:
        todo.scheduled = todo.due

    todo.due = None


@event.listens_for(Todo, "before_update")
def update_scheduled_for_recurrence(mapper, connection, todo: Todo):
    """
    Bounces a ticked-off recurring todo back to pending, one interval on

    A recurring todo is never finished, only done for now: ticking it off
    moves the day it is planned for forward by its interval and hands it
    straight back, pending. The tick never lands and the row never moves,
    which is why the pane flashes it instead.
    """

    if todo.recurrence is None:
        return

    if todo.scheduled is None:
        todo.scheduled = datetime.now()

    if todo.pending:
        return

    todo.pending = True
    todo.scheduled += todo.recurrence
