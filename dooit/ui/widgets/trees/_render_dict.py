from typing import TYPE_CHECKING, Dict, Generic, TypeVar

from dooit.models import Todo, Workspace
from dooit.ui.widgets.renderers import (
    BaseRenderer,
    TodoRender,
    WorkspaceRender,
)

T = TypeVar("T", bound=BaseRenderer)

if TYPE_CHECKING:  # pragma: no cover
    from .model_tree import ModelTree


class RenderDict(Dict, Generic[T]):
    """
    Default Dict implementation for Todo/Workspace Renderers
    """

    def __init__(self, tree: "ModelTree"):
        super().__init__()
        self.tree = tree

    def from_id(self, _id: str) -> T:
        raise NotImplementedError  # pragma: no cover

    def __getitem__(self, __key: str) -> T:
        return super().__getitem__(__key)

    def __missing__(self, key: str) -> T:
        self[key] = self.from_id(key)
        return self[key]


class WorkspaceRenderDict(RenderDict[WorkspaceRender]):
    """
    Default Dict implementation for Workspace Renderers
    """

    def from_id(self, _id: str) -> WorkspaceRender:
        w = Workspace.from_id(_id)
        return WorkspaceRender(w, self.tree)


class TodoRenderDict(RenderDict[TodoRender]):
    """
    Default Dict implementation for Todo Renderers
    """

    def from_id(self, _id: str) -> TodoRender:
        t = Todo.from_id(_id)
        return TodoRender(t, self.tree)
