from typing import TYPE_CHECKING, List, Optional, Union
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
    BORDER_TITLE = "Todos"

    def __init__(self, model: Model) -> None:
        super().__init__(model, TodoRenderDict(self))

    def _get_parent(self, id: str) -> Optional[Todo]:
        return Todo.from_id(id).parent_todo

    def is_node_expaned(self, _id: str) -> bool:
        return super().is_node_expaned(_id) or self.api.vars.always_expand_todos

    def visible_children(self, model: Model) -> List[Model]:
        children = super().visible_children(model)
        if self.api.vars.hide_completed:
            return [todo for todo in children if todo.pending]

        return children

    def _force_refresh(self) -> None:
        super()._force_refresh()

        title = self.BORDER_TITLE
        if self.api.vars.hide_completed:
            title += " (completed hidden)"
        self.border_title = title

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

    def before_remove(self, model: Model) -> None:
        assert isinstance(model, Todo)
        self.post_message(TodoRemoved(model))

    def toggle_complete(self):
        assert isinstance(self.current_model, Todo)

        self.current_model.toggle_complete()
        self.force_refresh()  # completing a recurring todo adds a child

    def increase_urgency(self):
        assert isinstance(self.current_model, Todo)

        self.current_model.increase_urgency()
        self.update_current_prompt()

    def decrease_urgency(self):
        assert isinstance(self.current_model, Todo)

        self.current_model.decrease_urgency()
        self.update_current_prompt()

    @on(ModelTree.OptionHighlighted)
    def todo_highlighted(self, event: ModelTree.OptionHighlighted):
        assert event.option_id

        event.stop()
        self.post_message(TodoSelected(Todo.from_id(event.option_id)))
