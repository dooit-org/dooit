from .base_renderer import BaseRenderer, Workspace
from ..inputs.model_inputs import WorkspaceDescription, WorkspaceTasks


class WorkspaceRender(BaseRenderer[Workspace]):
    @property
    def model(self) -> Workspace:
        return self._model

    def post_init(self):
        self.description = WorkspaceDescription(self.model)
        self.tasks = WorkspaceTasks(self.model)
