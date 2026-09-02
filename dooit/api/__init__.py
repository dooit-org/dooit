from .model import DooitModel, BaseModel
from .todo import Todo
from .workspace import Workspace
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

    for workspace in Workspace.all():
        if is_blank(workspace) and not workspace.workspaces and not workspace.todos:
            workspace.drop()

    for todo in Todo.all():
        if is_blank(todo) and not todo.todos:
            todo.drop()


__all__ = [
    "BaseModel",
    "DooitModel",
    "Todo",
    "Workspace",
    "manager",
    "drop_blank_models",
    "fix_hooks",
    "validation_hooks",
    "update_hooks",
]
