from typing import TYPE_CHECKING, List, Optional, Union
from textual import on
from textual.color import Color
from textual.strip import Strip
from textual.style import Style
from textual.widgets.option_list import Option

from dooit.api import Todo, Workspace
from dooit.ui.api.events import TodoRemoved
from dooit.ui.api.events.events import TodoSelected
from dooit.utils import blend
from .model_tree import ModelTree
from ..renderers.todo_renderer import TodoRender
from ._render_dict import TodoRenderDict

if TYPE_CHECKING:  # pragma: no cover
    from ...api.api_components.formatters.model_formatters import (
        TodoFormatter,
    )

Model = Union[Todo, Workspace]


class TodosTree(ModelTree[Model, TodoRenderDict]):
    BORDER_TITLE = "TODOS"
    show_header = True

    # How far every other row is pulled from the pane background towards the
    # lighter one behind it. Just enough to keep a row's columns tied together
    # across the width of the pane, and well short of the step the highlight
    # takes, so that the cursor never reads as banding.
    #
    # Only this pane bands its rows: a todo carries columns off to the right
    # that have to be read back to their description, where a workspace is
    # little more than its name.
    ROW_SHADE = 0.4

    def __init__(self, model: Model) -> None:
        super().__init__(model, TodoRenderDict(self))

    @property
    def row_shade(self) -> Color:
        """The background the shaded half of the rows sits on"""

        theme = self.api.vars.theme
        return Color.parse(blend(theme.background1, theme.background2, self.ROW_SHADE))

    @property
    def _body_offset(self) -> int:
        """Index of the first row that is a todo rather than the column header"""

        if self._options and self._options[0].id == self.HEADER_ID:
            return 1

        return 0

    def _is_shaded(self, index: int) -> bool:
        """
        Whether the option at `index` is one of the banded rows

        Counted from the first todo so that the header never shifts the
        banding, and offset by one so that the topmost todo stays plain.
        """

        if not self.api.vars.row_shading:
            return False

        row = index - self._body_offset
        return row >= 0 and bool(row % 2)

    def _get_option_render(self, option: Option, style: Style) -> List[Strip]:
        """
        Bands the rows, leaving the highlighted one to the cursor

        The shade is dropped for the highlighted row rather than drawn under
        it, so that the cursor is the only background in play wherever it sits
        """

        index = self._option_to_index.get(option)

        if index is not None and index != self.highlighted and self._is_shaded(index):
            style += Style(background=self.row_shade)

        return super()._get_option_render(option, style)

    def _get_parent(self, id: str) -> Optional[Todo]:
        return Todo.from_id(id).parent_todo

    def is_node_expaned(self, _id: str) -> bool:
        return super().is_node_expaned(_id) or self.api.vars.always_expand_todos

    @property
    def formatter(self) -> "TodoFormatter":
        return self.api.formatter.todos

    @property
    def render_layout(self):
        return self.api.layouts.todo_layout

    def add_todo(self) -> str:
        todo = self.model.add_todo()
        render = TodoRender(todo, tree=self)
        self.add_option(Option(render.prompt, id=render.id))
        return todo.uuid

    def _add_first_item(self) -> Todo:
        return self.model.add_todo()

    def _create_child_node(self) -> Todo:
        return self.current_model.add_todo()

    def _remove_node(self) -> None:
        assert isinstance(self.current_model, Todo)
        self.post_message(TodoRemoved(self.current_model))

        return super()._remove_node()

    def toggle_complete(self):
        assert isinstance(self.current_model, Todo)

        self.current_model.toggle_complete()
        self.refresh_options()

    def set_priority(self, priority: int):
        assert isinstance(self.current_model, Todo)

        self.current_model.set_priority(priority)
        self.update_current_prompt()

    @on(ModelTree.OptionHighlighted)
    def todo_highlighted(self, event: ModelTree.OptionHighlighted):
        assert event.option_id

        event.stop()
        self.post_message(TodoSelected(Todo.from_id(event.option_id)))
