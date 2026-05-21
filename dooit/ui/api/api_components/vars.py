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
    """
    Manages application-level variables and state for the Dooit application.
    Provides access to configuration flags, the current mode, theme,
    and references to the workspace and todo tree widgets and their models.
    """

    def __init__(self, api: "DooitAPI") -> None:
        super().__init__()
        self.api = api
        self._show_confirm = True
        self._always_expand_workspaces = False
        self._always_expand_todos = False

    @property
    def always_expand_workspaces(self) -> bool:
        """Return whether workspace nodes should always be expanded."""
        return self._always_expand_workspaces

    @always_expand_workspaces.setter
    def always_expand_workspaces(self, value: bool):
        """Set whether workspace nodes should always be expanded."""
        self._always_expand_workspaces = value

    @property
    def always_expand_todos(self) -> bool:
        """Return whether todo nodes should always be expanded."""
        return self._always_expand_todos

    @always_expand_todos.setter
    def always_expand_todos(self, value: bool):
        """Set whether todo nodes should always be expanded."""
        self._always_expand_todos = value

    @property
    def show_confirm(self):
        """Return whether confirmation prompts are enabled."""
        return self._show_confirm

    @show_confirm.setter
    def show_confirm(self, value: bool):
        """Set whether confirmation prompts are enabled."""
        self._show_confirm = value

    @property
    def mode(self) -> str:
        """Return the current Dooit application mode."""
        return self.api.app.dooit_mode

    @property
    def theme(self) -> DooitThemeBase:
        """Return the current Dooit theme."""
        return self.api.css.theme

    @property
    def workspaces_tree(self) -> WorkspacesTree:
        """Return the workspaces tree widget from the current screen."""
        return self.api.app.screen.query_one(WorkspacesTree)

    @property
    def current_workspace(self) -> Optional[Workspace]:
        """Return the currently highlighted workspace, or None if nothing is highlighted."""
        tree = self.api.vars.workspaces_tree
        if tree.highlighted is None:
            return None

        return tree.current_model

    @property
    def todos_tree(self) -> Optional[TodosTree]:
        """Return the currently visible todos tree widget, or None if not visible."""
        todo_switcher = self.api.app.screen.query_one(
            "#todo_switcher", expect_type=ContentSwitcher
        )
        if todo_switcher.visible_content and isinstance(
            todo_switcher.visible_content, TodosTree
        ):
            return todo_switcher.visible_content

    @property
    def current_todo(self) -> Optional[Todo]:
        """Return the currently highlighted todo item, or None if nothing is highlighted."""
        tree = self.todos_tree
        if tree is None:
            return

        if tree.highlighted is None:
            return

        todo = tree.current_model
        assert isinstance(todo, Todo)

        return todo
