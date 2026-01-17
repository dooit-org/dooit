from typing import TYPE_CHECKING, Generic, List, TypeVar, Union
from rich.console import RenderableType
from rich.table import Table
from dooit.api import Todo, Workspace
from ..inputs.simple_input import SimpleInput

ModelType = TypeVar("ModelType", bound=Union[Todo, Workspace])

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

    def make_renderable(self) -> Table:
        layout = self.table_layout

        table = Table.grid(expand=True, padding=(0, 1), pad_edge=True)
        row = []

        if nest := self.model.nest_level:
            table.add_column("padding", width=2 * nest)
            row.append("")

        for attr in layout:
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

            if attr == "description":
                table.add_column(attr, ratio=1)
            else:
                table.add_column(attr, width=self._get_max_width(attr))

            row.append(rendered)

        table.add_row(*row)
        return table

    def start_edit(self, param: str) -> bool:
        if not hasattr(self, param):
            return False

        getattr(self, param).start_edit()
        self.editing = param
        return True

    def stop_edit(self):
        getattr(self, self.editing).stop_edit()
        self.tree.get_column_width.cache_clear()
        self.editing = ""

    def handle_keypress(self, key: str) -> bool:
        getattr(self, self.editing).keypress(key)
        return True
