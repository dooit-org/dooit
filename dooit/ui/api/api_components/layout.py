from textual.app import App
from dooit.ui.api.widgets import TodoLayout, ProjectLayout
from dooit.ui.widgets.trees import TodosTree, ProjectsTree
from ._base import ApiComponent


class LayoutManager(ApiComponent):
    def __init__(self, app: App) -> None:
        self.app = app
        self._todo_layout: TodoLayout = []
        self._project_layout: ProjectLayout = []

    @property
    def todo_layout(self) -> TodoLayout:
        return self._todo_layout

    @todo_layout.setter
    def todo_layout(self, layout: TodoLayout):
        self._todo_layout = layout
        for tree in self.app.screen.query(TodosTree):
            tree.refresh_options()

    @property
    def project_layout(self) -> ProjectLayout:
        return self._project_layout

    @project_layout.setter
    def project_layout(self, layout: ProjectLayout):
        self._project_layout = layout
        for tree in self.app.screen.query(ProjectsTree):
            tree.refresh_options()
