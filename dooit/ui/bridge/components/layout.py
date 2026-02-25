from dooit.config.config import (
    AppConfig,
    TodoLayoutConfig,
    WorkspaceLayoutConfig,
)

from ._base import ApiComponent


class LayoutManager(ApiComponent):
    def __init__(self) -> None:
        self.todo_layout: TodoLayoutConfig
        self.workspace_layout: WorkspaceLayoutConfig

    @classmethod
    def from_config(cls, config: AppConfig):
        instance = cls()
        instance.todo_layout = config.layout.todo
        instance.workspace_layout = config.layout.workspace
        return instance

    def set_todo_layout(self, layout: TodoLayoutConfig) -> None:
        self.todo_layout = layout

    def set_workspace_layout(self, layout: WorkspaceLayoutConfig) -> None:
        self.workspace_layout = layout
