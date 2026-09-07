from datetime import datetime
from sqlalchemy import event, update
from ..todo import Todo


@event.listens_for(Todo, "before_update")
def update_children_to_pending(_, connection, target: Todo):
    if not target.pending:
        return

    if any(todo.pending for todo in target.todos):
        return

    query = (
        update(Todo)
        .where(Todo.parent_todo_id == target.id)
        .values(pending=True, completed_at=None)
    )
    connection.execute(query)


@event.listens_for(Todo, "before_update")
def update_children_to_completed(_, connection, target: Todo):
    if target.pending:
        return

    query = (
        update(Todo)
        .where(Todo.parent_todo_id == target.id)
        .values(pending=False, completed_at=target.completed_at or datetime.now())
    )
    connection.execute(query)


@event.listens_for(Todo, "before_update")
def update_parent_to_pending(mapper, connection, target: Todo):
    if not target.pending or not target.parent_todo:
        return

    query = (
        update(Todo)
        .where(Todo.id == target.parent_todo_id)
        .values(pending=True, completed_at=None)
    )
    connection.execute(query)


@event.listens_for(Todo, "before_update")
def update_parent_to_completed(mapper, connection, target: Todo):
    if target.pending or not target.parent_todo:
        return

    parent = target.parent_todo
    all_sibling_completed = all([not sibling.pending for sibling in parent.todos])
    if all_sibling_completed:
        query = (
            update(Todo)
            .where(Todo.id == target.parent_todo_id)
            .values(pending=False, completed_at=target.completed_at or datetime.now())
        )
        connection.execute(query)


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
