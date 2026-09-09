from typing import TYPE_CHECKING, Optional

from textual.widgets import ContentSwitcher

from dooit.api import Project, TodoSortModeType
from dooit.api.theme import DooitThemeBase
from dooit.api.todo import Todo
from dooit.ui.widgets.trees import ProjectsTree, TodosTree
from ._base import ApiComponent


if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


class VarManager(ApiComponent):
    def __init__(self, api: "DooitAPI") -> None:
        super().__init__()
        self.api = api
        self._show_confirm = True
        self._always_expand_projects = False
        self._always_expand_todos = False
        self._row_shading = False
        self._todo_sort: TodoSortModeType = "priority"

    @property
    def todo_sort(self) -> TodoSortModeType:
        """
        The order the todos of a stored project are read in

        Priority to start with: a project is a pile of work, and what is asked
        of it first is what to do next. An order picked instead of it belongs
        to the pane rather than to the project that was open at the time, and
        holds until it is switched again.

        Fixed projects order their own rows and are left alone by this.
        """

        return self._todo_sort

    @todo_sort.setter
    def todo_sort(self, value: TodoSortModeType):
        self._todo_sort = value

    @property
    def row_shading(self) -> bool:
        """Whether every other todo row is tinted to help the eye track it"""

        return self._row_shading

    @row_shading.setter
    def row_shading(self, value: bool):
        self._row_shading = value

    @property
    def always_expand_projects(self) -> bool:
        return self._always_expand_projects

    @always_expand_projects.setter
    def always_expand_projects(self, value: bool):
        self._always_expand_projects = value

    @property
    def always_expand_todos(self) -> bool:
        return self._always_expand_todos

    @always_expand_todos.setter
    def always_expand_todos(self, value: bool):
        self._always_expand_todos = value

    @property
    def show_confirm(self):
        return self._show_confirm

    @show_confirm.setter
    def show_confirm(self, value: bool):
        self._show_confirm = value

    @property
    def mode(self) -> str:
        return self.api.app.dooit_mode

    @property
    def theme(self) -> DooitThemeBase:
        return self.api.css.theme

    @property
    def projects_tree(self) -> ProjectsTree:
        return self.api.app.screen.query_one(ProjectsTree)

    @property
    def current_project(self) -> Optional[Project]:
        tree = self.api.vars.projects_tree
        if tree.highlighted is None:
            return None

        return tree.current_model

    @property
    def todos_tree(self) -> Optional[TodosTree]:
        todo_switcher = self.api.app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        )
        if todo_switcher.visible_content and isinstance(
            todo_switcher.visible_content, TodosTree
        ):
            return todo_switcher.visible_content

    @property
    def current_todo(self) -> Optional[Todo]:
        tree = self.todos_tree
        if tree is None:
            return

        if tree.highlighted is None:
            return

        todo = tree.current_model
        assert isinstance(todo, Todo)

        return todo
