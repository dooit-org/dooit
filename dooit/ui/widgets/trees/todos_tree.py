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
    BORDER_TITLE = "TODOS"
    show_header = True

    def __init__(self, model: Model) -> None:
        super().__init__(model, TodoRenderDict(self))

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
