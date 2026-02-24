from textual.app import App

from dooit.ui.widgets.trees.todos_tree import TodoLayout
from dooit.ui.widgets.trees.workspaces_tree import WorkspaceLayout

from ._base import ApiComponent


class LayoutManager(ApiComponent):
    def __init__(self, app: App) -> None:
        self.app = app
        self.todo_layout: TodoLayout = []
        self.workspace_layout: WorkspaceLayout = []

    def set_todo_layout(self, layout: TodoLayout) -> None:
        self.todo_layout = layout

    def set_workspace_layout(self, layout: WorkspaceLayout) -> None:
        self.workspace_layout = layout
