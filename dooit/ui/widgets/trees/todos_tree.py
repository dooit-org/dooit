from typing import TYPE_CHECKING, Dict, List, Optional, Union
from textual import on
from textual.color import Color
from textual.strip import Strip
from textual.style import Style
from textual.timer import Timer
from textual.widgets.option_list import Option

from dooit.api import Todo, Project
from dooit.ui.api.events import SpawnNote, TodoRemoved
from dooit.ui.api.events.events import TodoSelected
from dooit.utils import blend
from .model_tree import ModelTree
from ..renderers.todo_renderer import TodoRender
from ._render_dict import TodoRenderDict

if TYPE_CHECKING:  # pragma: no cover
    from ...api.api_components.formatters.model_formatters import (
        TodoFormatter,
    )

Model = Union[Todo, Project]


class TodosTree(ModelTree[Model, TodoRenderDict]):
    BORDER_TITLE = "TASKS"
    show_header = True
    CHILDREN_ATTR = "todos"

    # How far every other row is pulled from the pane background towards the
    # lighter one behind it. Just enough to keep a row's columns tied together
    # across the width of the pane, and well short of the step the highlight
    # takes, so that the cursor never reads as banding.
    #
    # Only this pane bands its rows: a todo carries columns off to the right
    # that have to be read back to their description, where a project is
    # little more than its name.
    ROW_SHADE = 0.4

    # The pulse a recurring todo answers a tick with. Ticking one off never
    # takes the row anywhere: it comes straight back pending with its next date
    # set, so without this the key looks like it did nothing and gets pressed
    # again. The row lights up in the green the rest of the app says "done" in
    # and sinks back to the background it was on, over a third of a second —
    # long enough to catch out of the corner of an eye, short enough that it is
    # gone before the next key.
    FLASH_STEPS = 8
    FLASH_INTERVAL = 0.04
    FLASH_STRENGTH = 0.6

    def __init__(self, model: Model) -> None:
        super().__init__(model, TodoRenderDict(self))

        # Rows still fading, each with the steps it has left to go
        self._flashing: Dict[str, int] = {}
        self._flash_timer: Optional[Timer] = None

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

    def flash_row(self, _id: str) -> None:
        """Start the row at full brightness, and keep the fade running"""

        self._flashing[_id] = self.FLASH_STEPS

        if self._flash_timer is None:
            self._flash_timer = self.set_interval(self.FLASH_INTERVAL, self._fade_rows)

        self.refresh()

    def _fade_rows(self) -> None:
        """
        Takes every flashing row one step closer to the background it sits on

        The timer is stopped rather than left ticking once the last row has
        arrived, so that a pane nobody has touched costs nothing.
        """

        for _id, step in list(self._flashing.items()):
            if step <= 1:
                self._flashing.pop(_id)
            else:
                self._flashing[_id] = step - 1

        if not self._flashing and self._flash_timer is not None:
            self._flash_timer.stop()
            self._flash_timer = None

        self.refresh()

    def _flash_background(self, step: int, under: Optional[Color]) -> Color:
        """The green a flashing row sits on, `step` steps into the fade"""

        theme = self.api.vars.theme
        base = under or Color.parse(theme.background1)
        strength = self.FLASH_STRENGTH * step / self.FLASH_STEPS

        return base.blend(Color.parse(theme.green), strength)

    def _get_option_render(self, option: Option, style: Style) -> List[Strip]:
        """
        Bands the rows, leaving the highlighted one to the cursor

        The shade is dropped for the highlighted row rather than drawn under
        it, so that the cursor is the only background in play wherever it sits.

        A row still flashing overrides both: it is mixed into whatever
        background it would otherwise have had, so that when the green has
        drained away the row is left exactly as it started, cursor and all.
        """

        index = self._option_to_index.get(option)
        step = self._flashing.get(option.id or "")

        if step:
            style += Style(background=self._flash_background(step, style.background))
        elif index is not None and index != self.highlighted and self._is_shaded(index):
            style += Style(background=self.row_shade)

        return super()._get_option_render(option, style)

    def visible_children(self, model: Model) -> List[Todo]:
        """
        The todos of this model that the pane has a row for

        A task is what moves: a completed todo filed straight under a project
        has gone to the Completed project, is shown there with everything that
        was finished along with it, and comes back here when it is unticked.

        A completed step of a task has gone nowhere. It stays under the todo
        it belongs to, ticked off, for as long as there is anything left to do
        in that todo — which is what makes the parent a task in progress
        rather than a row that empties out as it is worked on.
        """

        if isinstance(model, Todo):
            return list(model.todos)

        return [todo for todo in model.todos if todo.pending]

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

    def _delete_current_model(self) -> None:
        assert isinstance(self.current_model, Todo)
        self.post_message(TodoRemoved(self.current_model))

        return super()._delete_current_model()

    def toggle_complete(self):
        todo = self.current_model
        assert isinstance(todo, Todo)

        was_scheduled_for = todo.scheduled

        todo.toggle_complete()
        self.refresh_options()

        # A recurring todo is handed back pending with its next date already
        # set, so the only thing the tick changed is the day it is planned for:
        # the flash is what says so. Every other row says it for itself, by
        # moving out of the pane.
        if todo.scheduled != was_scheduled_for:
            self.flash_row(todo.uuid)

    def set_priority(self, priority: int):
        assert isinstance(self.current_model, Todo)

        self.current_model.set_priority(priority)
        self.update_current_prompt()

    def set_effort(self, effort: int):
        assert isinstance(self.current_model, Todo)

        self.current_model.set_effort(effort)
        self.update_current_prompt()

    def show_note(self):
        assert isinstance(self.current_model, Todo)

        # Posted rather than pushed from here: the screen package imports the
        # trees, so reaching the other way would close the circle
        self.post_message(SpawnNote(self.current_model))

    @on(ModelTree.OptionHighlighted)
    def todo_highlighted(self, event: ModelTree.OptionHighlighted):
        assert event.option_id

        event.stop()

        if self.is_static_row(event.option_id):
            return

        self.post_message(TodoSelected(Todo.from_id(event.option_id)))
