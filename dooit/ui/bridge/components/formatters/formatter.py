from dooit.config.config import AppConfig

from .._base import ApiComponent
from .model_formatters import TodoFormatter, WorkspaceFormatter


class Formatter(ApiComponent):
    def __init__(self) -> None:
        self.todos = TodoFormatter()
        self.workspaces = WorkspaceFormatter()

    @classmethod
    def from_config(cls, config: AppConfig):
        instance = cls()
        instance.todos.description.set(config.formatter.todo.description)
        instance.todos.due.set(config.formatter.todo.due)
        instance.todos.urgency.set(config.formatter.todo.urgency)
        instance.todos.effort.set(config.formatter.todo.effort)
        instance.todos.status.set(config.formatter.todo.status)
        instance.todos.recurrence.set(config.formatter.todo.recurrence)
        instance.workspaces.description.set(config.formatter.workspace.description)

        return instance
