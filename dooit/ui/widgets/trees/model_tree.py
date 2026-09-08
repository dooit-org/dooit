from collections import defaultdict
from functools import cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    TypeVar,
    Union,
)
from textual.app import ComposeResult
from rich.cells import cell_len
from rich.console import Console, ConsoleOptions, Group, RenderableType, RenderResult
from rich.measure import Measurement
from rich.segment import Segment
from rich.table import Table
from rich.text import Text
from textual.color import Color
from textual.strip import Strip
from textual.style import Style
from textual.timer import Timer
from textual.widgets import Label
from textual.widgets.option_list import Option, OptionDoesNotExist
from dooit.api import Todo, Project
from dooit.ui.api.events import (
    ModeChanged,
    StartSort,
    BarNotification,
)
from dooit.ui.widgets.renderers import BaseRenderer, COLUMN_PADDING
from dooit.utils import copy_text, paste_text
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

class ColumnRule:
    """
    A hairline drawn the full width of the pane, under the column titles

    It takes whatever width it is handed and asks for none of its own, so the
    columns keep sizing themselves off the titles and the nodes alone.

    The blank lines it can be given above it are what pushes whatever follows
    it down: a rule with a gap over it is how a block is pinned to the foot of
    a pane that is otherwise filled from the top.
    """

    CHARACTER = "─"

    def __init__(self, style: str, space_above: int = 0) -> None:
        self.style = style
        self.space_above = space_above

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for _ in range(self.space_above):
            yield Segment.line()

        yield Segment(self.CHARACTER * options.max_width, console.get_style(self.style))
        yield Segment.line()

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        return Measurement(0, 0)


class GroupHeading:
    """
    The name of a block of rows, with a hairline running out to the pane edge

    Same hairline the column titles sit on, so a block reads as a smaller
    version of the header that opens the pane. The blank line above it is what
    separates one block from the rows of the one before.
    """

    CHARACTER = "─"

    def __init__(
        self,
        label: str,
        label_style: str,
        rule_style: str,
        space_above: bool = True,
    ) -> None:
        self.label = label
        self.label_style = label_style
        self.rule_style = rule_style
        self.space_above = space_above

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        if self.space_above:
            yield Segment.line()

        # Indented by what the rows pad their leftmost column with, so the
        # label starts where the columns underneath it do
        label = f"{' ' * COLUMN_PADDING}{self.label} "
        yield Segment(label, console.get_style(self.label_style))

        rule = self.CHARACTER * max(0, options.max_width - cell_len(label))
        yield Segment(rule, console.get_style(self.rule_style))
        yield Segment.line()

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        return Measurement(0, 0)


ModelType = TypeVar("ModelType", bound=Union[Todo, Project])
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

    HEADER_ID = "dooit-column-header"
    show_header: bool = False

    # The attribute a node's children hang off, walked into when the node is
    # expanded: "projects" for the projects pane, "todos" for the tasks pane
    CHILDREN_ATTR: str = ""

    # Whether a nested row is drawn hanging off the row above it. A pane that
    # gathers its rows from all over the tree shows them as the flat list they
    # are, since the parent a guide would point back at is not on screen
    show_guides: bool = True

    # Rounded caps drawn on either side of the border title so that the title
    # bar matches the rounded pane borders
    TITLE_CAP_LEFT = "\ue0b6"
    TITLE_CAP_RIGHT = "\ue0b4"

    # The pulse a row answers a key with when the key changed something the
    # row cannot show by moving: a recurring todo handed straight back pending,
    # a project rebuilt to take a revived todo back. The row lights up in the
    # green the rest of the app says "done" in and sinks back to the background
    # it was on, over a third of a second \u2014 long enough to catch out of the
    # corner of an eye, short enough that it is gone before the next key.
    FLASH_STEPS = 8
    FLASH_INTERVAL = 0.04
    FLASH_STRENGTH = 0.6

    def __init__(self, model: ModelType, render_dict: RenderDictType) -> None:
        tree = self.__class__.__name__
        super().__init__(id=f"{tree}_{model.uuid}")
        self._model = model
        self.expaned = defaultdict(bool)
        self._renderers: RenderDictType = render_dict
        self._static_rows: Dict[str, Callable[[], RenderableType]] = {}

        # Rows still fading, each with the steps it has left to go
        self._flashing: Dict[str, int] = {}
        self._flash_timer: Optional[Timer] = None

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
        Mixes the flash into whatever background the row would otherwise have

        Whatever it was \u2014 the pane's own, the cursor's, a banded row's \u2014 is
        what the row is left on once the green has drained away.
        """

        step = self._flashing.get(option.id or "")

        if step:
            style += Style(background=self._flash_background(step, style.background))

        return super()._get_option_render(option, style)

    @cache
    def get_column_width(self, attr: str) -> int:
        width = max(i._get_attr_width(attr) for i in self._renderers.values())

        if self.show_header:
            width = max(width, len(self.column_title(attr)))

        return width

    # Column headers that shouldn't just be the attribute name spelled out
    COLUMN_TITLES: Dict[str, str] = {}

    @classmethod
    def column_title(cls, attr: str) -> str:
        return cls.COLUMN_TITLES.get(attr, attr.replace("_", " ").title())

    def make_header(self) -> RenderableType:
        """
        Renders the column names, aligned with the columns of the nodes, over a
        rule that sets them off from the nodes below
        """

        table = Table.grid(expand=True, padding=(0, COLUMN_PADDING), pad_edge=True)
        row = []

        style = f"bold {self.api.vars.theme.primary}"

        for index, item in enumerate(self.render_layout):
            attr = item.value

            if attr == "description":
                table.add_column(attr, ratio=1)
            else:
                width = self.get_column_width(attr)

                # the leftmost column has to hold the table edge padding as well
                if index == 0:
                    width += COLUMN_PADDING

                table.add_column(attr, width=width)

            row.append(Text(self.column_title(attr), style=style))

        table.add_row(*row)
        return Group(table, ColumnRule(self.api.vars.theme.background3))

    def static_row(self, _id: str, make: Callable[[], RenderableType]) -> Option:
        """
        A row that stands for no model: the column titles, a rule, a heading

        It is drawn from `make` on every refresh rather than once, so that a
        theme change reaches it, and it is disabled, which is what keeps the
        cursor from ever landing on something there is nothing to do with.
        """

        self._static_rows[_id] = make
        return Option("", id=_id, disabled=True)

    def is_static_row(self, _id: Optional[str]) -> bool:
        return _id is None or _id in self._static_rows

    def prompt_for(self, _id: str) -> RenderableType:
        make = self._static_rows.get(_id)

        if make is not None:
            return make()

        return self._renderers[_id].prompt

    def row_note(self, model: ModelType) -> Text:
        """
        What this pane has to add to a row, drawn after its description

        Nothing, for a pane whose rows are all filed under the same thing; a
        pane that gathers its rows from across the tree overrides this to say
        where each of them came from.
        """

        return Text()

    @property
    def formatter(self) -> "ModelFormatterBase":
        raise NotImplementedError  # pragma: no cover

    @property
    def render_layout(self) -> Any:
        raise NotImplementedError  # pragma: no cover

    def column_value(self, attr: str, component: Any) -> Any:
        """
        The value a column is formatted from

        What the field holds, unless the pane has reason to show something
        coarser than that.
        """

        return component.model_value

    @property
    def editable_columns(self) -> List[str]:
        """
        The columns an edit may be started on

        Everything the pane draws, and for a pane that leaves a column out,
        that column too: it is hidden because it has nothing to add, not
        because there is nothing behind it to change.
        """

        return [item.value for item in self.render_layout]

    @property
    def current(self) -> BaseRenderer:
        _id = self.node.id
        assert _id is not None

        return self._renderers[_id]

    @property
    def current_model(self) -> ModelType:
        return self.current.model

    @property
    def is_fixed_node(self) -> bool:
        """
        Whether the cursor is on a fixed project rather than a stored model
        """

        if self.highlighted is None or self.is_static_row(self.node.id):
            return False

        return getattr(self.current_model, "is_fixed", False)

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

    @property
    def is_editing(self) -> bool:
        return self.highlighted is not None and self.current.editing != ""

    @property
    def model(self) -> ModelType:
        return self._model

    @property
    def empty_message(self) -> Label:
        return self.query_one("#empty_message", expect_type=Label)

    def force_refresh(self) -> None:
        self._refresh_and_restore_highlight()

        if self.has_focus:
            self.highlight_first_node()

    @fix_highlight
    def _refresh_and_restore_highlight(self) -> None:
        self._force_refresh()
        self.get_column_width.cache_clear()

    def is_node_expaned(self, _id: str) -> bool:
        return self.expanded_nodes[_id]

    def visible_children(self, model: Any) -> List:
        """
        The children of a model that this pane has a row for

        Everything filed under it, for a pane that shows the tree as it stands;
        a pane that some of the models have moved out of leaves those out here.
        """

        return getattr(model, self.CHILDREN_ATTR)

    def _model_options(self) -> List[Option]:
        """
        One row per model, each expanded node followed by the rows under it
        """

        options: List[Option] = []

        def add_children_recurse(model: ModelType):
            for child in self.visible_children(model):
                render = self._renderers[child.uuid]
                options.append(Option("", id=render.id))

                if self.is_node_expaned(child.uuid):
                    add_children_recurse(child)

        add_children_recurse(self.model)
        return options

    def _body_options(self) -> List[Option]:
        """
        Every row of the pane bar the column titles

        This is what a pane that shows more than the models under its own root
        overrides: what it hands back is drawn in the order it comes in.
        """

        return self._model_options()

    def _build_options(self) -> List[Option]:
        options = self._body_options()

        if options and self.show_header:
            options.insert(0, self.static_row(self.HEADER_ID, self.make_header))

        return options

    def _ensure_enabled_highlight(self) -> None:
        """
        Moves the cursor off a row it cannot sit on

        Rows come and go as the tree is refreshed, so an index that pointed at
        a node can end up on a rule or a heading, or past the end of the pane
        entirely; the cursor is nudged down to the next row that is really
        there.
        """

        if self.highlighted is None or not self._options:
            return

        start = min(self.highlighted, len(self._options) - 1)

        for index in range(start, len(self._options)):
            if not self._options[index].disabled:
                self.highlighted = index
                return

        # Nothing below to fall onto: back to the top of the pane, or off the
        # rows entirely if every last one of them is a rule or a heading
        first = self.first_selectable_index
        self.highlighted = first if not self._options[first].disabled else None

    def _force_refresh(self) -> None:
        highlighted = self.highlighted
        self.clear_options()
        self._static_rows.clear()

        options = self._build_options()
        has_nodes = any(not self.is_static_row(option.id) for option in options)

        self.add_options(options)

        if not options:
            highlighted = None
        elif highlighted is not None:
            highlighted = min(
                max(highlighted, self.first_selectable_index),
                len(options) - 1,
            )

        self.highlighted = highlighted
        self._ensure_enabled_highlight()

        self.empty_message.display = not has_nodes
        self.refresh_options()

    def on_mount(self):
        self.force_refresh()
        self.refresh_border_title()

    def refresh_border_title(self) -> None:
        """
        Renders the pane title as a pill with rounded ends
        """

        if not self.is_mounted or not self.BORDER_TITLE:
            return

        theme = self.api.vars.theme
        if self.has_focus:
            fill, text = theme.primary, theme.background1
        else:
            fill, text = theme.background3, theme.foreground1

        cap = f"{fill} on {theme.background1}"
        self.border_title = (
            f"[{cap}]{self.TITLE_CAP_LEFT}[/]"
            f"[{text} on {fill}]{self.BORDER_TITLE}[/]"
            f"[{cap}]{self.TITLE_CAP_RIGHT}[/]"
        )

    def watch_has_focus(self, has_focus: bool) -> None:
        super().watch_has_focus(has_focus)
        self.refresh_border_title()

    def notify_style_update(self) -> None:
        super().notify_style_update()
        self.refresh_border_title()

    @require_highlighted_node
    def start_sort(self):
        self.post_message(StartSort(self.current_model, self.sort))

    def start_edit(self, property: str) -> bool:
        if property not in self.editable_columns:
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

    def stop_edit(self, cancel: bool = False):
        """
        End the edit, keeping what was typed unless it is being thrown away

        A cancelled edit leaves the model exactly as it was, which still lets
        a brand new item fall through the blank-description check below: it
        was never given a name, so there is nothing to keep it for.
        """

        edited = self.current.editing

        try:
            self.current.stop_edit(cancel)
        except Exception as e:  # pragma: no cover
            self.post_message(BarNotification(str(e), "error"))

        self.app.post_message(ModeChanged("NORMAL"))
        self.get_column_width.cache_clear()

        # An item without a description is nothing at all: one that is left
        # blank (or all whitespace) is dropped instead of being kept around.
        # An item that carries children is worth a confirmation first, since
        # dropping it takes everything under it along
        if edited == "description" and not self.current_model.description.strip():
            if self._current_has_children:
                self._remove_node()
            else:
                self._discard_node()

            return

        self.update_current_prompt()

    async def handle_keypress(self, key: str) -> bool:
        if self.is_editing:
            if key in ["escape", "enter"]:
                # enter keeps what was typed; escape throws it away and puts
                # the field back the way it was found
                self.stop_edit(cancel=key == "escape")
            else:
                self.current.handle_keypress(key)

            self.update_current_prompt()
            return True
        else:
            if self.highlighted is not None:
                self.update_current_prompt()

        return True

    def refresh_options(self) -> None:
        for i in self._options:
            assert i.id is not None

            self.replace_option_prompt(i.id, self.prompt_for(i.id))

    def _get_parent(self, id: str) -> Optional[ModelType]:
        raise NotImplementedError  # pragma: no cover

    @require_highlighted_node
    def copy_description_to_clipboard(self):
        copy_text(self.app, self.current_model.description)

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

    def highlight_id_if_shown(self, _id: str) -> bool:
        """
        Puts the cursor on a row, if the pane happens to have one for it

        What is being pointed at can come from outside the pane -- the finder
        picks a task out of the database, not off the screen -- and a pane
        that does not draw it is a cursor that stays where it was rather than
        an error.
        """

        try:
            self.highlight_id(_id)
        except OptionDoesNotExist:
            return False

        return True

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

    def _new_sibling(self) -> Optional[ModelType]:
        """
        The empty node a new sibling starts out as, or None if there is none

        Whether a new node can be put here at all is answered once, rather
        than by each of the callers: a pane that has nowhere to keep one - or
        a tree that is in the middle of an edit - turns a paste away for the
        same reason it turns an `add_sibling` away.
        """

        if self.is_editing:
            return None

        if not self._options:
            return self.add_first_item()

        return self._add_sibling_node()

    def add_sibling(self):
        node = self._new_sibling()

        if node is None:
            return

        self.highlight_id(node.uuid)
        self.start_edit("description")

    @refresh_tree
    def _describe_node(self, node: ModelType, description: str) -> None:
        node.description = description
        node.save()

    def paste_as_sibling(self):
        """
        Add a node beside the highlighted one, described by the clipboard

        A description is one line, so the pasted text is squeezed onto one:
        anything else would leave a row drawn over the ones beneath it.
        """

        description = " ".join(paste_text(self.app).split())

        if not description:
            self.post_message(BarNotification("Clipboard is empty", "warning"))
            return

        node = self._new_sibling()

        if node is None:
            return

        self._describe_node(node, description)
        self.highlight_id(node.uuid)

    @property
    def _current_has_children(self) -> bool:
        model = self.current_model
        return bool(getattr(model, "projects", None) or getattr(model, "todos", None))

    def _delete_current_model(self) -> None:
        model = self.current_model

        self._renderers.pop(model.uuid)
        self.expanded_nodes.pop(model.uuid)
        model.drop()

    def forget_rows(self, ids: Iterable[str]) -> None:
        """
        Drops what the pane was keeping about rows that are gone for good

        A row is drawn out of a renderer the pane holds on to, and it holds
        one for every model it has ever drawn — including models that have
        since moved out of it, into the Bin or into another project. Measuring
        a column walks the whole lot of them, so a renderer left behind by a
        deleted model is a row read off the database after the row it belongs
        to has left it.
        """

        for _id in ids:
            self._renderers.pop(_id, None)
            self.expanded_nodes.pop(_id, None)

    @require_confirmation
    @refresh_tree
    def _remove_node(self):
        self._delete_current_model()

    @refresh_tree
    def _discard_node(self) -> None:
        """Drop the highlighted node without asking to confirm"""

        self._delete_current_model()

    def _bin_node(self) -> None:
        """
        Move the highlighted node to the Bin, keeping everything it holds
        """

        raise NotImplementedError  # pragma: no cover

    def _restore_node(self) -> None:
        """
        Take the highlighted node back out of the Bin
        """

        self.post_message(
            BarNotification("Only tasks in the Bin can be restored", "warning")
        )

    @require_highlighted_node
    @refresh_tree
    def remove_node(self):
        """
        Throws the highlighted item away

        Nothing goes for good here: what is dropped lands in the Bin, whole,
        and stays there until it is either restored or deleted on purpose.
        Which is what lets the key act on the spot instead of asking first.
        """

        self._bin_node()

    @require_highlighted_node
    def delete_node(self):
        """
        Deletes the highlighted item outright, with everything under it

        The one way something leaves the database, and the only edit that
        cannot be taken back — so it is the one that asks.
        """

        self._remove_node()

    @require_highlighted_node
    @refresh_tree
    def restore_node(self):
        """
        Puts the highlighted item back where it was thrown away from
        """

        self._restore_node()

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
