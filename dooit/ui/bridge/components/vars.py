from typing import TYPE_CHECKING, Optional

from textual.widgets import ContentSwitcher

from dooit.config.config import AppConfig, DooitTheme
from dooit.models import Workspace
from dooit.models.todo import Todo
from dooit.ui.widgets.trees import TodosTree, WorkspacesTree

from ._base import ApiComponent

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.bridge.dooit_api import DooitAPI


class VarManager(ApiComponent):
    def __init__(self, api: "DooitAPI") -> None:
        super().__init__()
        self.api = api
        self.show_confirm = True
        self.always_expand_workspaces = False
        self.always_expand_todos = False

    @classmethod
    def from_config(cls, config: AppConfig, api: "DooitAPI"):
        instance = cls(api)
        var_config = config.general
        for key, value in var_config.as_dict().items():
            if hasattr(instance, key) and not isinstance(
                getattr(type(instance), key, None), property
            ):
                setattr(instance, key, value)

        return instance

    @property
    def mode(self) -> str:
        return self.api.app.dooit_mode

    @property
    def theme(self) -> DooitTheme:
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
