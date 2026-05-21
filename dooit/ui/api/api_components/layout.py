from textual.app import App
from dooit.ui.api.widgets import TodoLayout, WorkspaceLayout
from dooit.ui.widgets.trees import TodosTree, WorkspacesTree
from ._base import ApiComponent


class LayoutManager(ApiComponent):
    """
    Manages the column layout configuration for workspace and todo trees
    in the Dooit application. Changes to layouts automatically refresh
    the corresponding tree widgets.
    """

    def __init__(self, app: App) -> None:
        self.app = app
        self._todo_layout: TodoLayout = []
        self._workspace_layout: WorkspaceLayout = []

    @property
    def todo_layout(self) -> TodoLayout:
        """Return the current todo tree column layout."""
        return self._todo_layout

    @todo_layout.setter
    def todo_layout(self, layout: TodoLayout):
        """Set the todo tree column layout and refresh all todo tree widgets."""
        self._todo_layout = layout
        for tree in self.app.screen.query(TodosTree):
            tree.refresh_options()

    @property
    def workspace_layout(self) -> WorkspaceLayout:
        """Return the current workspace tree column layout."""
        return self._workspace_layout

    @workspace_layout.setter
    def workspace_layout(self, layout: WorkspaceLayout):
        """Set the workspace tree column layout and refresh all workspace tree widgets."""
        self._workspace_layout = layout
        for tree in self.app.screen.query(WorkspacesTree):
            tree.refresh_options()
