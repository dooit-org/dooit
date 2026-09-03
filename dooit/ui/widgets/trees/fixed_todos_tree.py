from functools import partial
from typing import List, Set

from textual.widgets.option_list import Option

from dooit.api import FixedProject
from dooit.ui.api.events import BarNotification
from dooit.utils import blend
from .model_tree import GroupHeading
from .todos_tree import TodosTree

# How far a group heading is pulled towards the background. The block it opens
# has to be found without being read, so the name sits a step below the column
# titles above it and a step above the hairline it runs into
HEADING_FADE = 0.25


class FixedTodosTree(TodosTree):
    """
    The tasks of a fixed project, gathered from across the whole tree

    The rows are the same todos every other pane shows, in the same columns:
    what a fixed project adds is that they arrive from more than one project at
    once, so each block is opened by the project it was pulled out of.
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
