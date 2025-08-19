from collections import defaultdict
from functools import cache
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar, Union
from textual.app import ComposeResult
from textual.widgets import Label
from textual.widgets.option_list import Option
from dooit.api import Todo, Workspace
from dooit.ui.api.events import (
    ModeChanged,
    StartSearch,
    StartSort,
    BarNotification,
)
from dooit.ui.widgets.renderers import BaseRenderer
from .base_tree import BaseTree
from ._render_dict import RenderDict
from ._decorators import (
    fix_highlight,
    refresh_tree,
    require_highlighted_node,
    require_confirmation,
)

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.api_components.formatters._model_formatter_base import (
        ModelFormatterBase,
    )

ModelType = TypeVar("ModelType", bound=Union[Todo, Workspace])
RenderDictType = TypeVar("RenderDictType", bound=RenderDict)


class ModelTree(BaseTree, Generic[ModelType, RenderDictType]):
    DEFAULT_CSS = """
    ModelTree {
        height: 1fr;
        width: 1fr;
        align: center middle;

        & > Label {
            align: center middle;
        }
    }
    """

    def __init__(self, model: ModelType, render_dict: RenderDictType) -> None:
        tree = self.__class__.__name__
        super().__init__(id=f"{tree}_{model.uuid}")
        self._model = model
        self.expaned = defaultdict(bool)
        self._renderers: RenderDictType = render_dict
        self._filter_refresh = False
        self._model_clipboard = None

    @cache
    def get_column_width(self, attr: str) -> int:
        return max(i._get_attr_width(attr) for i in self._renderers.values())

    @property
    def formatter(self) -> "ModelFormatterBase":
        raise NotImplementedError  # pragma: no cover

    @property
    def render_layout(self) -> Any:
        raise NotImplementedError  # pragma: no cover

    @property
    def filter_refresh(self):
        return self._filter_refresh

    @filter_refresh.setter
    def filter_refresh(self, value: bool):
        refresh = self._filter_refresh != value
        self._filter_refresh = value

        if refresh:
            self.force_refresh()

    @property
    def current(self) -> BaseRenderer:
        _id = self.node.id
        assert _id is not None

        return self._renderers[_id]

    @property
    def current_model(self) -> ModelType:
        return self.current.model

    def update_prompt_at_index(self, index: int):
        option = self.get_option_at_index(index)
        assert option.id is not None

        self.update_prompt_by_id(option.id)

    def update_prompt_by_id(self, _id: str):
        renderer = self._renderers[_id]
        self.replace_option_prompt(_id, renderer.prompt)

    def update_current_prompt(self):
        if self.highlighted is not None:
            self.update_prompt_at_index(self.highlighted)
            self.scroll_to_highlight()

    def set_filter(self, filter: str) -> None:
        self.filter_refresh = bool(filter)

        for option in self._options:
            assert option.id
            matches = self._renderers[option.id].matches_filter(filter)
            if matches:
                self.enable_option(option.id)
            else:
                self.disable_option(option.id)

    @property
    def is_editing(self) -> bool:
        return self.highlighted is not None and self.current.editing != ""

    @property
    def model(self) -> ModelType:
        return self._model

    @property
    def empty_message(self) -> Label:
        return self.query_one("#empty_message", expect_type=Label)

    @fix_highlight
    def force_refresh(self) -> None:
        self._force_refresh()
        self.get_column_width.cache_clear()

    def is_node_expaned(self, _id: str) -> bool:
        return self.expanded_nodes[_id]

    def _force_refresh(self) -> None:
        highlighted = self.highlighted
        self.clear_options()

        options = []

        def add_children_recurse(model: ModelType):
            for child in getattr(
                model,
                self.__class__.__name__.replace("Tree", "").lower(),
            ):
                render = self._renderers[child.uuid]
                options.append(Option("", id=render.id))

                if self.is_node_expaned(child.uuid) or self.filter_refresh:
                    add_children_recurse(child)

        add_children_recurse(self.model)
        self.add_options(options)
        self.highlighted = highlighted

        has_options = bool(options)
        self.empty_message.display = not has_options
        self.refresh_options()

    def on_mount(self):
        self.force_refresh()

    @require_highlighted_node
    def start_sort(self):
        self.post_message(StartSort(self.current_model, self.sort))

    @require_highlighted_node
    def start_search(self):
        self.post_message(StartSearch(self.set_filter))

    def start_edit(self, property: str) -> bool:
        columns = [i.value for i in self.render_layout]
        if property not in columns:
            self.post_message(
                BarNotification(f"No such column: [b]{property}[/b]", "error")
            )
            return False

        res = self.current.start_edit(property)
        self.update_current_prompt()
        if res:
            self.app.post_message(ModeChanged("INSERT"))
            self.update_current_prompt()
        return res

    def stop_edit(self):
        try:
            self.current.stop_edit()
        except Exception as e:  # pragma: no cover
            self.post_message(BarNotification(str(e), "error"))

        self.app.post_message(ModeChanged("NORMAL"))
        self.get_column_width.cache_clear()
        self.update_current_prompt()

    def reset_state(self):
        """
        Reset tree of any modified status for e.g. search
        """
        self.set_filter("")

    async def handle_keypress(self, key: str) -> bool:
        if self.is_editing:
            if key in ["escape", "enter"]:
                self.stop_edit()
            else:
                self.current.handle_keypress(key)

            self.update_current_prompt()
            return True
        else:
            if key == "escape":
                self.reset_state()

            if self.highlighted is not None:
                self.update_current_prompt()

        return True

    def refresh_options(self) -> None:
        for i in self._options:
            assert i.id is not None
            new_prompt = self._renderers[i.id].prompt
            self.replace_option_prompt(i.id, new_prompt)

    def _get_parent(self, id: str) -> Optional[ModelType]:
        raise NotImplementedError  # pragma: no cover

    @require_highlighted_node
    def copy_description_to_clipboard(self):
        self.app.copy_to_clipboard(self.current_model.description)

    @refresh_tree
    def _expand_node(self, _id: str) -> None:
        self.expanded_nodes[_id] = True

    def expand_node(self) -> None:
        if self.highlighted is not None and self.node.id:
            self._expand_node(self.node.id)

    @refresh_tree
    def _collapse_node(self, _id: str) -> None:
        self.expanded_nodes[_id] = False

    def _toggle_expand_node(self, _id: str) -> None:
        expanded = self.expanded_nodes[_id]
        if expanded:
            self._collapse_node(_id)
        else:
            self._expand_node(_id)

    @require_highlighted_node
    def toggle_expand(self) -> None:
        self._toggle_expand_node(self.node.id)

    def _toggle_expand_parent(self, _id: str) -> None:
        parent = self._get_parent(_id)

        if not parent or getattr(parent, "is_root", False):
            return

        parent_id = parent.uuid
        self.highlight_id(parent_id)
        self._toggle_expand_node(parent_id)

    @require_highlighted_node
    def toggle_expand_parent(self) -> None:
        self._toggle_expand_parent(self.node.id)

    def _create_child_node(self) -> ModelType:
        raise NotImplementedError  # pragma: no cover

    def add_child_node(self):
        node = self._create_child_node()
        node.description = ""
        node.save()

        self.expand_node()
        self.highlight_id(node.uuid)
        self.start_edit("description")

    def _create_sibling_node(self) -> ModelType:
        return self.current_model.add_sibling()

    def highlight_id(self, _id: str):
        self.highlighted = self.get_option_index(_id)

    @refresh_tree
    def _add_sibling_node(self) -> ModelType:
        node = self._create_sibling_node()
        node.description = ""
        node.save()
        return node

    @refresh_tree
    def add_first_item(self) -> ModelType:
        return self._add_first_item()

    def _add_first_item(self) -> ModelType:
        raise NotImplementedError  # pragma: no cover

    def add_sibling(self):
        if self.is_editing:
            return

        if not self._options:
            node = self.add_first_item()
        else:
            node = self._add_sibling_node()

        self.highlight_id(node.uuid)
        self.start_edit("description")

    @require_confirmation
    @refresh_tree
    def _remove_node(self):
        model = self.current_model

        self._renderers.pop(model.uuid)
        self.expanded_nodes.pop(model.uuid)
        model.drop()

    @require_highlighted_node
    def copy_model_to_clipboard(self):
        node_type = self.current_model.__class__.__name__
        self.api.notify(f"{node_type} was copied to clipboard")
        self._model_clipboard = self.current_model.id

    def paste_model_from_clipboard(
        self, position: str = "below"
    ) -> Optional[ModelType]:
        @refresh_tree
        def add_node(self):
            if not self._model_clipboard:
                self.post_message(BarNotification("No model in clipboard", "error"))
                return None

            if position not in ["below", "above"]:
                self.post_message(
                    BarNotification("Invalid position, use 'below' or 'above'", "error")
                )
                return None

            if not self.highlighted:
                order_index = len(self._options)
            else:
                order_index = self.current_model.order_index
                if position == "below":
                    order_index += 1

            if isinstance(self.current_model, Todo):
                new_model = Todo.clone_from_id(self._model_clipboard, order_index)
            else:
                new_model = Workspace.clone_from_id(self._model_clipboard, order_index)

            return new_model

        model = add_node(self)
        self.highlight_id(model.uuid)
        return model

    @require_highlighted_node
    def remove_node(self):
        self._remove_node()

    @refresh_tree
    def shift_up(self) -> None:
        self.current_model.shift_up()

    @refresh_tree
    def shift_down(self):
        self.current_model.shift_down()

    @refresh_tree
    def sort(self, attr: str):
        if attr == "reverse":
            self.current_model.reverse_siblings()
        else:
            self.current_model.sort_siblings(attr)

    def show_help(self):
        self.app.push_screen("help")

    def compose(self) -> ComposeResult:
        with Label(id="empty_message"):
            yield Label("No items to display")
