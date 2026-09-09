from typing import TYPE_CHECKING, Generic, List, TypeVar, Union
from rich.console import RenderableType
from rich.style import Style
from rich.table import Table
from rich.text import Text
from dooit.api import Todo, Project
from dooit.utils import blend
from ..inputs.simple_input import SimpleInput

ModelType = TypeVar("ModelType", bound=Union[Todo, Project])

# space kept on either side of a column, so that neighbouring columns are
# separated by twice as much as the table edges get
COLUMN_PADDING = 2

# Guides drawn to the left of a nested item, in the same rounded style the pane
# borders use: a line drops out of the parent's first column and turns right
# into the first column of each of its children, the way a file tree does.
# All four are the same width, which is what one level of nesting indents by.
GUIDE_BRANCH = "├── "
GUIDE_LAST_BRANCH = "╰── "
GUIDE_VERTICAL = "│   "
GUIDE_BLANK = "    "

# How far the guides are pulled towards the pane background. Far enough that
# they stay behind the descriptions they indent, and short of the point where
# the shape of the tree stops being readable.
GUIDE_FADE = 0.45

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.widgets.trees.model_tree import ModelTree


class BaseRenderer(Generic[ModelType]):
    editing: str = ""

    def __init__(self, model: ModelType, tree: "ModelTree"):
        self._model = model
        self.tree = tree
        self.post_init()

    def post_init(self):  # pragma: no cover
        pass

    def _get_component(self, component: str) -> SimpleInput:
        return getattr(self, component)

    @property
    def id(self) -> str:
        return self._model.uuid

    @property
    def table_layout(self) -> List:
        return self.tree.render_layout

    @property
    def prompt(self) -> RenderableType:
        return self.make_renderable()

    @property
    def model(self) -> ModelType:
        raise NotImplementedError  # pragma: no cover

    def _cell_len(self, rendered) -> int:
        return rendered.cell_len if isinstance(rendered, Text) else len(rendered)

    def _get_attr_width(self, attr: str) -> int:
        component = self._get_component(attr)
        formatter = self.tree.formatter
        rendered: str = getattr(formatter, attr).format_value(
            self.tree.column_value(attr, component), component.model
        )

        # An editing field draws its buffer plus whatever hint it appends to it,
        # which is wider than the buffer alone: measure what actually gets drawn
        if component.is_editing:
            editing_width = self._cell_len(component.render_editing(self.theme))
        else:
            editing_width = len(component.value) + 1

        return max(editing_width, len(rendered))

    def _get_max_width(self, attr: str) -> int:
        return self.tree.get_column_width(attr)

    @property
    def theme(self):
        return self.tree.api.vars.theme

    @property
    def guide_style(self) -> Style:
        theme = self.theme
        return Style(color=blend(theme.foreground1, theme.background1, GUIDE_FADE))

    @property
    def tree_guide(self) -> Text:
        """
        The file tree style guides for this item, one level of nesting at a time

        The innermost level is the elbow the item itself hangs off; every level
        above it only says whether the line of that ancestor carries on past
        this row or has already run out of siblings.
        """

        if not self.tree.show_guides:
            return Text()

        node = self.model
        pieces: List[str] = []

        while node.nest_level:
            last = node.is_last_sibling()

            if pieces:
                pieces.append(GUIDE_BLANK if last else GUIDE_VERTICAL)
            else:
                pieces.append(GUIDE_LAST_BRANCH if last else GUIDE_BRANCH)

            node = node.parent

        if not pieces:
            return Text()

        # assembled rather than styled as a whole, so that the color stays on
        # the guides instead of bleeding into whatever gets appended to them
        return Text.assemble(("".join(reversed(pieces)), self.guide_style))

    def _with_row_note(self, rendered: RenderableType) -> RenderableType:
        """
        The description with whatever the pane has to say about the row after it
        """

        note = self.tree.row_note(self.model)

        if not note.cell_len:
            return rendered

        cell = Table.grid(expand=True)
        cell.add_column(ratio=1)
        cell.add_column(justify="right", no_wrap=True, width=note.cell_len)
        cell.add_row(rendered, note)

        return cell

    def make_renderable(self) -> Table:
        layout = self.table_layout

        table = Table.grid(expand=True, padding=(0, COLUMN_PADDING), pad_edge=True)
        row = []

        guide = self.tree_guide

        for index, item in enumerate(layout):
            attr = item.value
            component = self._get_component(attr)

            if component.is_editing:
                rendered = component.render_editing(self.theme)
            else:
                formatter = self.tree.formatter
                rendered = getattr(formatter, attr).format_value(
                    self.tree.column_value(attr, component), component.model
                )

            # Measured on what is about to be drawn, so that a field which grows
            # while it is edited gets the column widened for it
            if self._cell_len(rendered) > self._get_max_width(attr):
                self.tree.get_column_width.cache_clear()

            # The guides ride along inside the first cell rather than in a
            # column of their own, so that nothing separates the line from the
            # column it reaches into
            if index == 0 and guide.cell_len:
                rendered = guide + rendered

            # A pane's note on the row shares the description's column
            # rather than taking one of its own: pushed to the far end of it,
            # kept on one line, and left out of the width check above, since
            # it is the pane's word about the row and not the field's. What is
            # left of the column goes to the description, which wraps into it
            # exactly as it would have without a note.
            if attr == "description" and not component.is_editing:
                rendered = self._with_row_note(rendered)

            if attr == "description":
                table.add_column(attr, ratio=1)
            else:
                width = self._get_max_width(attr)

                # the leftmost column has to hold the table edge padding as
                # well, plus the guides drawn in front of it: widening it is
                # what pushes a nested row to the right
                if index == 0:
                    width += COLUMN_PADDING + guide.cell_len

                table.add_column(attr, width=width)

            row.append(rendered)

        table.add_row(*row)
        return table

    def start_edit(self, param: str) -> bool:
        if not hasattr(self, param):
            return False

        component = self._get_component(param)
        if not component.editable:
            return False

        component.start_edit()
        self.editing = param
        return True

    def stop_edit(self, cancel: bool = False):
        # A field that rejects what was typed raises out of here, and the tree
        # turns that into a notification. The edit still has to be torn down on
        # the way out, or the tree keeps routing keystrokes into the buffer
        # while the bar claims to be back in NORMAL mode
        try:
            getattr(self, self.editing).stop_edit(cancel)
        finally:
            self.tree.get_column_width.cache_clear()
            self.editing = ""

    def handle_keypress(self, key: str) -> bool:
        getattr(self, self.editing).keypress(key)
        return True
