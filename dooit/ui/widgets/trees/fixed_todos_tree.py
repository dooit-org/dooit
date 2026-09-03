from datetime import datetime
from functools import partial
from typing import Any, List, Set

from rich.style import Style
from rich.text import Text
from textual.widgets.option_list import Option

from dooit.api import FixedProject, Todo
from dooit.api.fixed_projects import owning_project
from dooit.ui.api.events import BarNotification, StartFieldEdit
from dooit.utils import blend
from .model_tree import GroupHeading
from .todos_tree import TodosTree

# How far a group heading is pulled towards the background. The block it opens
# has to be found without being read, so the name sits a step below the column
# titles above it and a step above the hairline it runs into
HEADING_FADE = 0.25

# The folder the projects pane draws its rows with, so a row that names its
# project here is recognisably pointing back at a row over there
OWNER_ICON = "󰉋"

# How far the project trailing a row is pulled towards the background. Further
# than anything else on the row: it is there to be found once a row has been
# read, never to be scanned down the pane.
OWNER_FADE = 0.55


class FixedTodosTree(TodosTree):
    """
    The tasks of a fixed project, gathered from across the whole tree

    The rows are the same todos every other pane shows, in the same columns:
    what a fixed project adds is that they arrive from more than one project at
    once, in blocks under whatever heading it chose to gather them by. A
    project that groups by anything but the project itself has each row say
    where it came from, since its headings no longer do.
    """

    show_guides = False

    def __init__(self, model: FixedProject) -> None:
        super().__init__(model)
        self._shaded_rows: Set[int] = set()

    @property
    def model(self) -> FixedProject:
        return self._model

    def _heading_id(self, index: int) -> str:
        return f"dooit-todo-group-{index}"

    def _make_heading(self, label: str, space_above: bool) -> GroupHeading:
        theme = self.api.vars.theme

        return GroupHeading(
            label=label,
            label_style=blend(theme.foreground1, theme.background1, HEADING_FADE),
            rule_style=theme.background3,
            space_above=space_above,
        )

    def _body_options(self) -> List[Option]:
        """
        Every block of the fixed project, each under the name it belongs to

        The banding is worked out here rather than off the row index, so that a
        heading never counts as a row and every block starts unshaded.
        """

        options: List[Option] = []
        self._shaded_rows = set()

        for index, group in enumerate(self.model.todo_groups):
            if group.label:
                options.append(
                    self.static_row(
                        self._heading_id(index),
                        partial(self._make_heading, group.label, bool(index)),
                    )
                )

            for row, todo in enumerate(group.todos):
                if row % 2:
                    self._shaded_rows.add(len(options))

                options.append(Option("", id=self._renderers[todo.uuid].id))

        return options

    @property
    def render_layout(self) -> List:
        """
        The columns of the pane, less the ones its headings already say
        """

        hidden = set(self.model.hidden_columns)

        if not hidden:
            return super().render_layout

        return [item for item in super().render_layout if item.value not in hidden]

    @property
    def editable_columns(self) -> List[str]:
        """
        A column left out of the pane is still a column of the todo behind it
        """

        return [item.value for item in super().render_layout]

    def column_value(self, attr: str, component: Any) -> Any:
        """
        A day-only column handed to the formatters as the day it falls on

        The pane is read a day at a time, so the hour is noise beside the
        headings. Rounding the value down is what leaves it out, rather than
        the pane having any say in how a date is written.
        """

        value = super().column_value(attr, component)

        if attr in self.model.day_only_columns and isinstance(value, datetime):
            return value.replace(hour=0, minute=0, second=0, microsecond=0)

        return value

    def start_edit(self, property: str) -> bool:
        started = super().start_edit(property)

        # Nowhere in the row to draw the buffer, so the bar takes it. Making
        # room for the column instead would shift the whole pane sideways the
        # moment an edit started, and back again the moment it ended.
        if started and property in self.model.hidden_columns:
            self.post_message(StartFieldEdit(self, property))

        return started

    def row_note(self, model) -> Text:
        """
        The project a row was pulled out of, at the far end of its description

        Only for the fixed projects grouped by something other than the
        project: the ones with a block per project have said it already. What
        it shows is the project's own name rather than its whole path, which
        is what keeps it to the end of a line it is sharing.
        """

        if not self.model.show_owning_project or not isinstance(model, Todo):
            return Text()

        project = owning_project(model)

        if project is None:  # pragma: no cover
            return Text()

        theme = self.api.vars.theme
        style = Style(color=blend(theme.foreground1, theme.background1, OWNER_FADE))

        return Text(f"  {OWNER_ICON} {project.description}", style=style)

    def _is_shaded(self, index: int) -> bool:
        if not self.api.vars.row_shading:
            return False

        return (index - self._body_offset) in self._shaded_rows

    # ---------------------------------------------------------------
    # A fixed project owns none of the todos it shows: they can be worked on
    # here, but where they live and what order they come in is decided by the
    # project they really belong to
    # ---------------------------------------------------------------

    def _not_here(self, what: str) -> None:
        self.post_message(
            BarNotification(f"{what} in [b]{self.model.title}[/b]", "warning")
        )

    def add_sibling(self):
        self._not_here("Tasks can't be added")

    def add_child_node(self):
        self._not_here("Tasks can't be added")

    def shift_up(self) -> None:
        self._not_here("Tasks can't be reordered")

    def shift_down(self):
        self._not_here("Tasks can't be reordered")

    def start_sort(self):
        self._not_here("Tasks can't be sorted")

    def paste_model_from_clipboard(self, position: str = "below"):
        self._not_here("Tasks can't be pasted")
