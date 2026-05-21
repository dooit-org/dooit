from .base_renderer import BaseRenderer, Workspace
from ..inputs.model_inputs import WorkspaceDescription


class WorkspaceRender(BaseRenderer[Workspace]):
    """
    Renderer for Workspace model items.

    Manages the input component for the editable Workspace description attribute.
    """

    @property
    def model(self) -> Workspace:
        """Return the underlying Workspace model."""
        return self._model

    def post_init(self):
        """Initialize the input component for the Workspace description."""
        self.description = WorkspaceDescription(self.model)
