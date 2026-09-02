from typing import TYPE_CHECKING, Generic, List, TypeVar, Union
from rich.console import RenderableType
from rich.style import Style
from rich.table import Table
from rich.text import Text
from dooit.api import Todo, Workspace
from dooit.utils import blend
from ..inputs.simple_input import SimpleInput

ModelType = TypeVar("ModelType", bound=Union[Todo, Workspace])

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

    def matches_filter(self, filter: str) -> bool:
        return filter in self.model.description

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

    def _get_attr_width(self, attr: str) -> int:
        component = self._get_component(attr)
        formatter = self.tree.formatter
        rendered: str = getattr(formatter, attr).format_value(
            component.model_value, component.model
        )

        return max(len(component.value) + 1, len(rendered))

    def _get_max_width(self, attr: str) -> int:
        return self.tree.get_column_width(attr)

    @property
    def guide_style(self) -> Style:
        theme = self.tree.api.vars.theme
        return Style(color=blend(theme.foreground1, theme.background1, GUIDE_FADE))

    @property
    def tree_guide(self) -> Text:
        """
        The file tree style guides for this item, one level of nesting at a time

        The innermost level is the elbow the item itself hangs off; every level
        above it only says whether the line of that ancestor carries on past
        this row or has already run out of siblings.
        """

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

    def make_renderable(self) -> Table:
        layout = self.table_layout

        table = Table.grid(expand=True, padding=(0, COLUMN_PADDING), pad_edge=True)
        row = []

        guide = self.tree_guide

        for index, item in enumerate(layout):
            attr = item.value
            component = self._get_component(attr)

            if len(component.render()) > self._get_max_width(attr):
                self.tree.get_column_width.cache_clear()

            if component.is_editing:
                rendered = component.render()
            else:
                formatter = self.tree.formatter
                rendered = getattr(formatter, attr).format_value(
                    component.model_value, component.model
                )

            # The guides ride along inside the first cell rather than in a
            # column of their own, so that nothing separates the line from the
            # column it reaches into
            if index == 0 and guide.cell_len:
                rendered = guide + rendered

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

    def stop_edit(self):
        getattr(self, self.editing).stop_edit()
        self.tree.get_column_width.cache_clear()
        self.editing = ""

    def handle_keypress(self, key: str) -> bool:
        getattr(self, self.editing).keypress(key)
        return True
