from typing import TYPE_CHECKING, Optional, Union
from textual import on
from textual.widgets.option_list import Option

from dooit.api import Todo, Workspace
from dooit.ui.api.events import TodoRemoved
from dooit.ui.api.events.events import TodoSelected
from .model_tree import ModelTree
from ..renderers.todo_renderer import TodoRender
from ._render_dict import TodoRenderDict

if TYPE_CHECKING:  # pragma: no cover
    from ...api.api_components.formatters.model_formatters import (
        TodoFormatter,
    )

Model = Union[Todo, Workspace]


class TodosTree(ModelTree[Model, TodoRenderDict]):
    """
    Tree widget for displaying and managing Todo items,
    with support for completion toggling and urgency adjustments.
    """

    BORDER_TITLE = "Todos"

    def __init__(self, model: Model) -> None:
        super().__init__(model, TodoRenderDict(self))

    def _get_parent(self, id: str) -> Optional[Todo]:
        return Todo.from_id(id).parent_todo

    def is_node_expaned(self, _id: str) -> bool:
        """Return whether the given todo node is expanded, respecting the always-expand setting."""
        return super().is_node_expaned(_id) or self.api.vars.always_expand_todos

    @property
    def formatter(self) -> "TodoFormatter":
        """Return the todo formatter from the API."""
        return self.api.formatter.todos

    @property
    def render_layout(self):
        """Return the todo layout configuration from the API."""
        return self.api.layouts.todo_layout

    def add_todo(self) -> str:
        """Add a new todo to the tree and return its UUID."""
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
        """Toggle the completion status of the current todo."""
        assert isinstance(self.current_model, Todo)

        self.current_model.toggle_complete()
        self.refresh_options()

    def increase_urgency(self):
        """Increase the urgency level of the current todo."""
        assert isinstance(self.current_model, Todo)

        self.current_model.increase_urgency()
        self.update_current_prompt()

    def decrease_urgency(self):
        """Decrease the urgency level of the current todo."""
        assert isinstance(self.current_model, Todo)

        self.current_model.decrease_urgency()
        self.update_current_prompt()

    @on(ModelTree.OptionHighlighted)
    def todo_highlighted(self, event: ModelTree.OptionHighlighted):
        """Handle a todo being highlighted by posting a TodoSelected event."""
        assert event.option_id

        event.stop()
        self.post_message(TodoSelected(Todo.from_id(event.option_id)))
