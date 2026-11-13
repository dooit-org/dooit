from collections import defaultdict
from functools import cache
from typing import TYPE_CHECKING, Any, Generic, List, Optional, TypeVar, Union
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
        self.expanded_nodes = defaultdict(bool)
        self._renderers: RenderDictType = render_dict
        self._filter_refresh = False
        self._model_clipboard = None
        self._new_node_id: Optional[str] = None
        self._search_term = ""

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

        first_match = None
        for index, option in enumerate(self._options):
            assert option.id
            matches = self._renderers[option.id].matches_filter(filter)
            if matches:
                self.enable_option(option.id)
                if first_match is None:
                    first_match = index
            else:
                self.disable_option(option.id)

        if filter and first_match is not None:
            self.highlighted = first_match

    def confirm_search(self, term: str) -> None:
        """Leave the filtered view on the current match, remembering the term"""

        match = self.current_model if self.highlighted is not None else None
        self._search_term = term
        self.set_filter("")

        if match is not None and term:
            self.reveal(match)

    def all_nodes(self) -> List[ModelType]:
        """Every listed node in display order, including collapsed ones"""

        nodes = []

        def add(model: ModelType):
            for child in self.visible_children(model):
                nodes.append(child)
                add(child)

        add(self.model)
        return nodes

    def reveal(self, model: ModelType) -> None:
        """Expand the ancestors of `model` and move the cursor to it"""

        parent = model.parent
        while parent is not None and parent != self.model:
            self.expanded_nodes[parent.uuid] = True
            parent = parent.parent

        self.force_refresh()
        self.highlight_id(model.uuid)

    def goto_search_hit(self, step: int = 1) -> None:
        if not self._search_term:
            self.post_message(BarNotification("No previous search", "error"))
            return

        nodes = self.all_nodes()
        hits = [
            index
            for index, node in enumerate(nodes)
            if self._renderers[node.uuid].matches_filter(self._search_term)
        ]
        if not hits:
            self.post_message(
                BarNotification(f"No match for [b]{self._search_term}[/b]", "error")
            )
            return

        current = -1
        if self.highlighted is not None:
            current = nodes.index(self.current_model)

        if step > 0:
            after = [index for index in hits if index > current]
            target = after[0] if after else hits[0]
        else:
            before = [index for index in hits if index < current]
            target = before[-1] if before else hits[-1]

        self.reveal(nodes[target])

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

    @property
    def children_attr(self) -> str:
        return self.__class__.__name__.replace("Tree", "").lower()

    def visible_children(self, model: ModelType) -> List[ModelType]:
        return getattr(model, self.children_attr)

    def has_children(self, model: ModelType) -> bool:
        return bool(self.visible_children(model))

    def subtree(self, model: ModelType) -> List[ModelType]:
        nodes = [model]
        for child in getattr(model, self.children_attr):
            nodes.extend(self.subtree(child))

        return nodes

    def is_collapsed_parent(self, model: ModelType) -> bool:
        if self.is_node_expaned(model.uuid) or self.filter_refresh:
            return False

        return self.has_children(model)

    def _force_refresh(self) -> None:
        highlighted = self.highlighted
        self.clear_options()

        options = []

        def add_children_recurse(model: ModelType):
            for child in self.visible_children(model):
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

        if self._options and self.highlighted is None:
            self.highlighted = 0

    @require_highlighted_node
    def start_sort(self):
        self.post_message(StartSort(self.current_model, self.sort))

    @require_highlighted_node
    def start_search(self):
        self.post_message(StartSearch(self.set_filter, self.confirm_search))

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

        # an item added and left without a description is discarded
        new_node_id, self._new_node_id = self._new_node_id, None
        if new_node_id == self.node.id and not self.current_model.description:
            self._drop_node(self.current_model)

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
        self._new_node_id = node.uuid
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
        self._new_node_id = node.uuid
        self.start_edit("description")

    @require_confirmation
    def _remove_node(self):
        self._drop_node(self.current_model)

    @refresh_tree
    def _drop_node(self, model: ModelType):
        self.before_remove(model)

        # ids of deleted rows get reused, so drop cached state for all of them
        for node in self.subtree(model):
            self._renderers.pop(node.uuid, None)
            self.expanded_nodes.pop(node.uuid, None)

        model.drop()

    def before_remove(self, model: ModelType) -> None:
        """Called once the removal of `model` is confirmed, before it is deleted"""

    @require_highlighted_node
    def copy_model_to_clipboard(self):
        model = self.current_model
        node_type = model.__class__.__name__
        self.api.notify(f"{node_type} was copied to clipboard")

        # keep the contents, not the id, so it can be pasted after deletion
        self._model_clipboard = (type(model), model._snapshot())

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

            if self.highlighted is None:
                order_index = len(self._options)
                parent = self.model
            else:
                order_index = self.current_model.order_index
                parent = self.current_model.parent
                if position == "below":
                    order_index += 1

            model_class, snapshot = self._model_clipboard
            return model_class._from_snapshot(snapshot, parent, order_index)

        model = add_node(self)
        if model is not None:
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
