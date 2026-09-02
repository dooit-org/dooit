from collections.abc import Callable
from rich.console import Group, RenderableType
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult

from dooit.ui.api.api_components.keys import KeyManager
from .base import BaseScreen
from textual.widgets import Static


class DooitKeyTable(Static):
    DEFAULT_CSS = """
    DooitKeyTable {
        content-align: center middle;
        width: 80%;
        margin: 1;
        padding: 1 2;
    }
    """

    COMPONENT_CLASSES = {
        "keybind",
        "arrow",
        "description",
        "table-title",
        "separator",
    }
    BORDER_TITLE = "Key Bindings"

    def __init__(self, keybinds: KeyManager, no_op: Callable):
        super().__init__()
        self.keybinds = keybinds
        self.no_op = no_op

    def _render_group(self, group: str, key_width: int) -> RenderableType:
        t = Table.grid(expand=True, padding=(0, 1))
        # A fixed key column keeps the arrows lined up across every section;
        # the description soaks up whatever width is left over
        t.add_column("key", width=key_width)
        t.add_column("arrow", width=2)
        t.add_column("description", ratio=1)

        for keybind, func in self.keybinds.get_keybinds_by_group(group):
            if func.description == "<NOP>":
                continue

            t.add_row(
                Text(keybind, style=self.get_component_rich_style("keybind")),
                Text("->", style=self.get_component_rich_style("arrow")),
                Text(
                    func.description,
                    style=self.get_component_rich_style("description"),
                ),
            )

        return t

    def render(self) -> RenderableType:
        separator = Rule(
            characters="─",
            style=self.get_component_rich_style("separator"),
        )

        key_width = max(
            (
                len(keybind)
                for group in self.keybinds.groups
                for keybind, func in self.keybinds.get_keybinds_by_group(group)
                if func.description != "<NOP>"
            ),
            default=0,
        )

        renderables = []

        for group in self.keybinds.groups:
            # A blank line either side keeps the separator from crowding the
            # sections it divides
            if renderables:
                renderables += [Text(""), separator, Text("")]

            if group:
                title = Text(group, style=self.get_component_rich_style("table-title"))
                title.pad(1)
                renderables += [title, Text("")]

            renderables.append(self._render_group(group, key_width))

        return Group(*renderables)


class HelpScreen(BaseScreen):
    """
    Help Screen to view Help Menu
    """

    DEFAULT_CSS = """
    HelpScreen {
        align: center top;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Pop screen"),
    ]

    def compose(self) -> ComposeResult:
        yield DooitKeyTable(self.api.keys, self.api.no_op)

    def key_down(self):
        self.scroll_down()

    def key_up(self):
        self.scroll_up()

    def key_k(self):
        self.scroll_up()

    def key_l(self):
        self.scroll_down()
