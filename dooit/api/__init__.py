from .model import DooitModel, BaseModel
from .todo import Todo
from .project import Project
from .manager import manager
from .hooks import fix_hooks, validation_hooks, update_hooks


def drop_blank_models() -> None:
    """
    Drops every childless item whose description is blank

    Items are created before they are named, so quitting mid-edit can leave one
    behind with nothing in it. Anything holding children is left alone, so that
    a stray blank name can never take todos down with it.
    """

    def is_blank(model) -> bool:
        return not (model.description or "").strip()

    for project in Project.all():
        if is_blank(project) and not project.projects and not project.todos:
            project.drop()

    for todo in Todo.all():
        if is_blank(todo) and not todo.todos:
            todo.drop()


__all__ = [
    "BaseModel",
    "DooitModel",
    "Todo",
    "Project",
    "manager",
    "drop_blank_models",
    "fix_hooks",
    "validation_hooks",
    "update_hooks",
]
