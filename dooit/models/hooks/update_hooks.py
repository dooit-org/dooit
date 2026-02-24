from datetime import datetime
from sqlalchemy import event, update
from ..todo import Todo


@event.listens_for(Todo, "before_update")
def update_children_to_pending(_, connection, target: Todo):
    if not target.pending:
        return

    if any(todo.pending for todo in target.todos):
        return

    query = update(Todo).where(Todo.parent_todo_id == target.id).values(pending=True)
    connection.execute(query)


@event.listens_for(Todo, "before_update")
def update_children_to_completed(_, connection, target: Todo):
    if target.pending:
        return

    query = update(Todo).where(Todo.parent_todo_id == target.id).values(pending=False)
    connection.execute(query)


@event.listens_for(Todo, "before_update")
def update_parent_to_pending(mapper, connection, target: Todo):
    if not target.pending or not target.parent_todo:
        return

    query = update(Todo).where(Todo.id == target.parent_todo_id).values(pending=True)
    connection.execute(query)


@event.listens_for(Todo, "before_update")
def update_parent_to_completed(mapper, connection, target: Todo):
    if target.pending or not target.parent_todo:
        return

    parent = target.parent_todo
    all_sibling_completed = all([not sibling.pending for sibling in parent.todos])
    if all_sibling_completed:
        query = (
            update(Todo).where(Todo.id == target.parent_todo_id).values(pending=False)
        )
        connection.execute(query)


@event.listens_for(Todo, "before_update")
def update_due_for_recurrence(mapper, connection, todo: Todo):
    if todo.recurrence is None:
        return

    if todo.due is None:
        todo.due = datetime.now()

    if todo.pending:
        return

    todo.pending = True
    todo.due += todo.recurrence
