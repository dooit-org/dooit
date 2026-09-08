from .model import DooitModel, BaseModel
from .todo import SORT_KEYS, Todo, TodoSortModeType, sort_todos
from .project import Project
from .pinned_note import PINNED_NOTE_ID, PinnedNote
from .fixed_projects import (
    FixedProject,
    TodoGroup,
    TODAY,
    UPCOMING,
    COMPLETED,
    BIN,
    fixed_project_from_id,
    fixed_project_from_key,
    fixed_projects,
    register_fixed_project,
    binned_tasks,
)
from .recycle import (
    REVIVED_PREFIX,
    empty_bin,
    move_project_to_bin,
    move_todo_to_bin,
    restore_todo,
    revive_home,
)
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
    "TodoSortModeType",
    "SORT_KEYS",
    "sort_todos",
    "Project",
    "PinnedNote",
    "PINNED_NOTE_ID",
    "FixedProject",
    "TodoGroup",
    "TODAY",
    "UPCOMING",
    "COMPLETED",
    "BIN",
    "REVIVED_PREFIX",
    "empty_bin",
    "move_project_to_bin",
    "move_todo_to_bin",
    "restore_todo",
    "revive_home",
    "fixed_project_from_id",
    "fixed_project_from_key",
    "fixed_projects",
    "register_fixed_project",
    "binned_tasks",
    "manager",
    "drop_blank_models",
    "fix_hooks",
    "validation_hooks",
    "update_hooks",
]
