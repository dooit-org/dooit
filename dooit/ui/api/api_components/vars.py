from typing import TYPE_CHECKING, Optional

from textual.widgets import ContentSwitcher

from dooit.api import Workspace
from dooit.api.theme import DooitThemeBase
from dooit.api.todo import Todo
from dooit.ui.widgets.trees import WorkspacesTree, TodosTree
from ._base import ApiComponent


if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


class VarManager(ApiComponent):
    def __init__(self, api: "DooitAPI") -> None:
        super().__init__()
        self.api = api
        self._show_confirm = True
        self._always_expand_workspaces = False
        self._always_expand_todos = False
        self._row_shading = False

    @property
    def row_shading(self) -> bool:
        """Whether every other todo row is tinted to help the eye track it"""

        return self._row_shading

    @row_shading.setter
    def row_shading(self, value: bool):
        self._row_shading = value

    @property
    def always_expand_workspaces(self) -> bool:
        return self._always_expand_workspaces

    @always_expand_workspaces.setter
    def always_expand_workspaces(self, value: bool):
        self._always_expand_workspaces = value

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
    def workspaces_tree(self) -> WorkspacesTree:
        return self.api.app.screen.query_one(WorkspacesTree)

    @property
    def current_workspace(self) -> Optional[Workspace]:
        tree = self.api.vars.workspaces_tree
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
