from dooit.api import Todo, Workspace


def workspace_description(workspace: Workspace, **kwargs):
    return str(workspace.description)


def todo_description(todo: Todo, **kwargs):
    return str(todo.description)


def todo_status(todo: Todo, **kwargs):
    return str(todo.status)


def todo_effort(todo: Todo, **kwargs):
    return str(todo.effort)


def todo_urgency(todo: Todo, **kwargs):
    return str(todo.urgency)


def todo_due(todo: Todo, **kwargs):
    return str(todo.due) if todo.due else ""


def todo_recurrence(todo: Todo, **kwargs):
    return str(todo.recurrence) if todo.recurrence else ""
