from typing import TYPE_CHECKING, List, Optional
from textual import on
from textual.widgets.option_list import Option

from dooit.api import Project, fixed_projects, move_project_to_bin
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

    # The rules that keep the fixed projects apart from the stored ones. Same
    # hairline the column titles sit on, so the blocks outside them read as
    # part of the pane's own furniture rather than as one more project
    FIXED_RULE_ID = "dooit-fixed-projects-rule"
    BOTTOM_RULE_ID = "dooit-bottom-projects-rule"

    FIXED_MESSAGE = "[b]{}[/b] is a fixed project and can't be changed"

    def __init__(self, model: Project) -> None:
        render_dict = ProjectRenderDict(self)
        super().__init__(model, render_dict)
        self._bottom_gap = 0

    def _body_options(self) -> List[Option]:
        """
        The fixed projects first, then everything the database holds, then the
        fixed projects that belong at the foot of the pane

        Each block is divided from the next by a rule, which is only drawn when
        there is something on the far side of it to divide from. The pinned
        block is pushed all the way down by the blank lines over its rule, so
        that it sits on the floor of the pane rather than under the last
        project.
        """

        top: List[Option] = []
        bottom: List[Option] = []

        for project in fixed_projects():
            option = Option("", id=self._renderers[project.uuid].id)
            (bottom if project.pinned_bottom else top).append(option)

        stored = self._model_options()
        options = list(top)

        if top and stored:
            options.append(self.static_row(self.FIXED_RULE_ID, self._make_fixed_rule))

        options += stored

        if bottom:
            if top or stored:
                options.append(
                    self.static_row(self.BOTTOM_RULE_ID, self._make_bottom_rule)
                )

            options += bottom

        return options

    def _make_fixed_rule(self) -> ColumnRule:
        return ColumnRule(self.api.vars.theme.background3)

    def _make_bottom_rule(self) -> ColumnRule:
        return ColumnRule(self.api.vars.theme.background3, space_above=self._bottom_gap)

    def _sync_bottom_gap(self) -> None:
        """
        Sizes the blank space that holds the pinned block against the floor

        Whatever the pane has room for beyond the rows already in it, which is
        nothing at all once they fill it: from there on the block is simply the
        last thing in the list, and scrolled down to like anything else.
        """

        if self.BOTTOM_RULE_ID not in self._static_rows:
            return

        height = self.scrollable_content_region.height
        if height <= 0:
            return

        heights = self._heights
        if len(heights) != len(self._options):
            return

        # The rule's own hairline is part of what is filled; only the blank
        # lines above it are the gap being sized here
        filled = sum(heights.values()) - self._bottom_gap
        gap = max(0, height - filled)

        if gap != self._bottom_gap:
            self._bottom_gap = gap
            self.refresh_options()

    def _force_refresh(self) -> None:
        super()._force_refresh()
        self._sync_bottom_gap()

    def on_resize(self, _) -> None:
        # A pane that got taller or shorter has a different amount of floor to
        # hold the pinned block against
        self._sync_bottom_gap()

    def _stored_indices(self) -> List[int]:
        """
        The rows of the pane that stand for a project the database holds

        The fixed blocks top and tail the pane and each of them already has a
        key that jumps straight to it, so they are left out here: the top and
        the bottom of the pane, as far as moving around it goes, are the first
        and the last stored project.
        """

        indices: List[int] = []

        for index, option in enumerate(self._options):
            if option.disabled or self.is_static_row(option.id):
                continue

            assert option.id is not None

            if getattr(self._renderers[option.id].model, "is_fixed", False):
                continue

            indices.append(index)

        return indices

    def action_first(self) -> None:
        indices = self._stored_indices()

        if not indices:
            return super().action_first()

        self.highlighted = indices[0]

    def action_last(self) -> None:
        indices = self._stored_indices()

        if not indices:
            return super().action_last()

        self.highlighted = indices[-1]

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

    def _bin_node(self) -> None:
        """
        Throws the highlighted project away, keeping what was filed in it

        The project row is the only part that actually goes: every task under
        it, and under the projects nested inside it, lands in the Bin carrying
        the path it came from. Restoring one of them from there builds the
        project back out of that path, so dropping a project is a decision
        that can be walked back one task at a time.
        """

        project = self.current_model

        self.post_message(ProjectRemoved(project))
        self._renderers.pop(project.uuid, None)
        self.expanded_nodes.pop(project.uuid, None)

        move_project_to_bin(project)

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
    def delete_node(self):
        return super().delete_node()

    @reject_fixed_node(FIXED_MESSAGE)
    def shift_up(self) -> None:
        return super().shift_up()

    @reject_fixed_node(FIXED_MESSAGE)
    def shift_down(self):
        return super().shift_down()

    @reject_fixed_node(FIXED_MESSAGE)
    def start_sort(self):
        return super().start_sort()

    def _new_sibling(self) -> Optional[Project]:
        """
        The empty project a new sibling starts out as

        A fixed project has no siblings to be added to, so from there the new
        project goes to the top level, which is where the stored ones begin.
        """

        if self.is_fixed_node:
            if self.is_editing:
                return None

            return self.add_first_item()

        return super()._new_sibling()

    @on(ModelTree.OptionHighlighted)
    def project_highlighted(self, event: ModelTree.OptionHighlighted):
        assert event.option_id

        event.stop()

        if self.is_static_row(event.option_id):
            return

        self.post_message(ProjectSelected(self._renderers[event.option_id].model))
