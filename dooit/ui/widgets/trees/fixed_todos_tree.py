from datetime import datetime
from functools import partial
from typing import Any, List, Set

from rich.style import Style
from rich.text import Text
from textual.widgets.option_list import Option

from dooit.api import FixedProject, Todo, TodoGroup
from dooit.api.fixed_projects import owning_project
from dooit.ui.api.events import BarNotification, StartFieldEdit
from dooit.ui.api.widgets import TodoWidget
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

# How much of a row a trailing project name may take before it is cut short.
# It shares a column with the description, which is the one thing on the row
# that has to stay readable, so a long project name gives way to it. A fixed
# cap rather than a share of the pane: a row is drawn once, and a pane that
# has just been opened has not been given its width yet
OWNER_MAX_WIDTH = 16

ELLIPSIS = "…"


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

    # Whether a row is followed by the todos filed under it. A fixed project
    # that gathers single todos from all over the tree draws one flat run of
    # rows; one whose rows are whole tasks draws each with its steps under it,
    # the way the project it came from did.
    show_children = False

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

    @property
    def todo_groups(self) -> List[TodoGroup]:
        """
        The blocks of rows the pane draws

        Whatever the fixed project gathered, which is the whole of it unless
        the pane is holding rows of its own alongside them.
        """

        return self.model.todo_groups

    def _body_options(self) -> List[Option]:
        """
        Every block of the fixed project, each under the name it belongs to

        The banding is worked out here rather than off the row index, so that a
        heading never counts as a row and every block starts unshaded.
        """

        options: List[Option] = []
        self._shaded_rows = set()

        for index, group in enumerate(self.todo_groups):
            if group.label:
                options.append(
                    self.static_row(
                        self._heading_id(index),
                        partial(self._make_heading, group.label, bool(index)),
                    )
                )

            for row, todo in enumerate(self._group_rows(group.todos)):
                if row % 2:
                    self._shaded_rows.add(len(options))

                options.append(Option("", id=self._renderers[todo.uuid].id))

        return options

    def _group_rows(self, todos: List[Todo]) -> List[Todo]:
        """
        The rows a block draws, in the order they are drawn in

        The todos the block gathered, each followed by whatever is filed under
        it for a pane that shows them, exactly as far as the node is expanded.
        """

        if not self.show_children:
            return list(todos)

        rows: List[Todo] = []

        for todo in todos:
            rows.append(todo)

            if self.is_node_expaned(todo.uuid) or self.filter_refresh:
                rows.extend(self._group_rows(self.visible_children(todo)))

        return rows

    @property
    def render_layout(self) -> List:
        """
        The columns of the pane: the layout's, less the ones its headings
        already say, plus whatever it has of its own to put there instead

        A column of its own goes in right behind the description, where the
        dates it stands in for would have been, rather than out at the end of
        the row past the columns nobody hid.
        """

        hidden = set(self.model.hidden_columns)
        layout = [item for item in super().render_layout if item.value not in hidden]

        extras = [TodoWidget(name) for name in self.model.extra_columns]
        extras = [item for item in extras if item not in layout]

        if not extras:
            return layout

        after = 0
        for index, item in enumerate(layout):
            if item.value == "description":
                after = index + 1
                break

        return layout[:after] + extras + layout[after:]

    @property
    def editable_columns(self) -> List[str]:
        """
        A column left out of the pane is still a column of the todo behind it
        """

        return [item.value for item in super().render_layout]

    def column_value(self, attr: str, component: Any) -> Any:
        return self._as_shown(attr, super().column_value(attr, component))

    def _as_shown(self, attr: str, value: Any) -> Any:
        """
        A day-only column handed to the formatters as the day it falls on

        The pane is read a day at a time, so the hour is noise beside the
        headings. Rounding the value down is what leaves it out, rather than
        the pane having any say in how a date is written.
        """

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

        return Text(f"  {OWNER_ICON} {self._fit(project.description)}", style=style)

    @staticmethod
    def _fit(name: str) -> str:
        """
        A project name cut down to what it may take of the row it trails
        """

        if len(name) <= OWNER_MAX_WIDTH:
            return name

        return name[: OWNER_MAX_WIDTH - 1] + ELLIPSIS

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

    def _new_sibling(self) -> None:
        self._not_here("Tasks can't be added")
        return None

    def add_child_node(self):
        self._not_here("Tasks can't be added")

    def shift_up(self) -> None:
        self._not_here("Tasks can't be reordered")

    def shift_down(self):
        self._not_here("Tasks can't be reordered")

    def start_sort(self):
        self._not_here("Tasks can't be sorted")
