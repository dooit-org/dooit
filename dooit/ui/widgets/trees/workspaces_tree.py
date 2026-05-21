from typing import TYPE_CHECKING, Optional
from textual import on
from textual.widgets.option_list import Option

from dooit.api import Workspace
from dooit.ui.api.events import (
    WorkspaceRemoved,
    WorkspaceSelected,
)
from .model_tree import ModelTree
from ._render_dict import WorkspaceRenderDict


if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.api_components.formatters.model_formatters import (
        WorkspaceFormatter,
    )


class WorkspacesTree(ModelTree[Workspace, WorkspaceRenderDict]):
    """
    Tree widget for displaying and managing Workspace items,
    with support for nested workspace hierarchies.
    """

    BORDER_TITLE = "Workspaces"

    def __init__(self, model: Workspace) -> None:
        render_dict = WorkspaceRenderDict(self)
        super().__init__(model, render_dict)

    def _get_parent(self, id: str) -> Optional[Workspace]:
        return Workspace.from_id(id).parent_workspace

    def is_node_expaned(self, _id: str) -> bool:
        """Return whether the given workspace node is expanded, respecting the always-expand setting."""
        return super().is_node_expaned(_id) or self.api.vars.always_expand_workspaces

    @property
    def formatter(self) -> "WorkspaceFormatter":
        """Return the workspace formatter from the API."""
        return self.api.formatter.workspaces

    @property
    def render_layout(self):
        """Return the workspace layout configuration from the API."""
        return self.api.layouts.workspace_layout

    def add_workspace(self) -> str:
        """Add a new workspace to the tree and return its UUID."""
        workspace = self.model.add_workspace()
        renderer = self._renderers[workspace.uuid]
        self.add_option(Option(renderer.prompt, id=renderer.id))
        return workspace.uuid

    def _create_child_node(self) -> Workspace:
        return self.current_model.add_workspace()

    def _add_first_item(self) -> Workspace:
        return self.model.add_workspace()

    def _remove_node(self) -> None:
        self.post_message(WorkspaceRemoved(self.current_model))
        return super()._remove_node()

    @on(ModelTree.OptionHighlighted)
    def workspace_highlighted(self, event: ModelTree.OptionHighlighted):
        """Handle a workspace being highlighted by posting a WorkspaceSelected event."""
        assert event.option_id

        event.stop()
        self.post_message(WorkspaceSelected(Workspace.from_id(event.option_id)))
