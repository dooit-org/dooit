from typing import TYPE_CHECKING, List, Optional
from textual import on
from textual.widgets.option_list import Option

from dooit.api import Project, fixed_projects
from dooit.ui.api.events import (
    ProjectRemoved,
    ProjectSelected,
)
from .model_tree import ColumnRule, ModelTree
from ._decorators import reject_fixed_node
from ._render_dict import ProjectRenderDict


if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.api_components.formatters.model_formatters import (
        ProjectFormatter,
    )


class ProjectsTree(ModelTree[Project, ProjectRenderDict]):
    BORDER_TITLE = "PROJECTS"
    show_header = True
    CHILDREN_ATTR = "projects"

    # A project's description is just what it's called
    COLUMN_TITLES = {"description": "Name"}

    # The rule that keeps the fixed projects apart from the stored ones. Same
    # hairline the column titles sit on, so the block above it reads as part
    # of the pane's own furniture rather than as one more project
    FIXED_RULE_ID = "dooit-fixed-projects-rule"

    FIXED_MESSAGE = "[b]{}[/b] is a fixed project and can't be changed"

    def __init__(self, model: Project) -> None:
        render_dict = ProjectRenderDict(self)
        super().__init__(model, render_dict)

    def _body_options(self) -> List[Option]:
        """
        The fixed projects first, then everything the database holds

        The two blocks are divided by a rule, which is only drawn when there is
        something on the far side of it to divide from.
        """

        fixed = [
            Option("", id=self._renderers[project.uuid].id)
            for project in fixed_projects()
        ]

        stored = self._model_options()

        if fixed and stored:
            fixed.append(self.static_row(self.FIXED_RULE_ID, self._make_fixed_rule))

        return fixed + stored

    def _make_fixed_rule(self) -> ColumnRule:
        return ColumnRule(self.api.vars.theme.background3)

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

    # ---------------------------------------------------------------
    # Nothing about a fixed project is stored, so every edit that would
    # write one back to the database is turned away with a word about why
    # ---------------------------------------------------------------

    @reject_fixed_node(FIXED_MESSAGE)
    def start_edit(self, property: str) -> bool:
        return super().start_edit(property)

    @reject_fixed_node(FIXED_MESSAGE)
    def add_child_node(self):
        return super().add_child_node()

    @reject_fixed_node(FIXED_MESSAGE)
    def remove_node(self):
        return super().remove_node()

    @reject_fixed_node(FIXED_MESSAGE)
    def shift_up(self) -> None:
        return super().shift_up()

    @reject_fixed_node(FIXED_MESSAGE)
    def shift_down(self):
        return super().shift_down()

    @reject_fixed_node(FIXED_MESSAGE)
    def start_sort(self):
        return super().start_sort()

    @reject_fixed_node(FIXED_MESSAGE)
    def copy_model_to_clipboard(self):
        return super().copy_model_to_clipboard()

    @reject_fixed_node(FIXED_MESSAGE)
    def paste_model_from_clipboard(self, position: str = "below"):
        return super().paste_model_from_clipboard(position)

    def add_sibling(self):
        """
        Adds a project beside the highlighted one

        A fixed project has no siblings to be added to, so from there the new
        project goes to the top level, which is where the stored ones begin.
        """

        if self.is_fixed_node:
            if self.is_editing:
                return

            node = self.add_first_item()
            self.highlight_id(node.uuid)
            self.start_edit("description")
            return

        return super().add_sibling()

    @on(ModelTree.OptionHighlighted)
    def project_highlighted(self, event: ModelTree.OptionHighlighted):
        assert event.option_id

        event.stop()

        if self.is_static_row(event.option_id):
            return

        self.post_message(ProjectSelected(self._renderers[event.option_id].model))
