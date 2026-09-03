from typing import TYPE_CHECKING, Optional
from textual import on
from textual.widgets.option_list import Option

from dooit.api import Project
from dooit.ui.api.events import (
    ProjectRemoved,
    ProjectSelected,
)
from .model_tree import ModelTree
from ._render_dict import ProjectRenderDict


if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.api_components.formatters.model_formatters import (
        ProjectFormatter,
    )


class ProjectsTree(ModelTree[Project, ProjectRenderDict]):
    BORDER_TITLE = "PROJECTS"
    show_header = True

    # A project's description is just what it's called
    COLUMN_TITLES = {"description": "Name"}

    def __init__(self, model: Project) -> None:
        render_dict = ProjectRenderDict(self)
        super().__init__(model, render_dict)

    def _get_parent(self, id: str) -> Optional[Project]:
        return Project.from_id(id).parent_project

    def is_node_expaned(self, _id: str) -> bool:
        return super().is_node_expaned(_id) or self.api.vars.always_expand_projects

    @property
    def formatter(self) -> "ProjectFormatter":
        return self.api.formatter.projects

    @property
    def render_layout(self):
        return self.api.layouts.project_layout

    def add_project(self) -> str:
        project = self.model.add_project()
        renderer = self._renderers[project.uuid]
        self.add_option(Option(renderer.prompt, id=renderer.id))
        return project.uuid

    def _create_child_node(self) -> Project:
        return self.current_model.add_project()

    def _add_first_item(self) -> Project:
        return self.model.add_project()

    def _delete_current_model(self) -> None:
        self.post_message(ProjectRemoved(self.current_model))
        return super()._delete_current_model()

    @on(ModelTree.OptionHighlighted)
    def project_highlighted(self, event: ModelTree.OptionHighlighted):
        assert event.option_id

        event.stop()
        self.post_message(ProjectSelected(Project.from_id(event.option_id)))
