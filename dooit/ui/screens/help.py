from collections.abc import Callable
from rich.console import Group, RenderableType
from rich.style import Style
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from dooit.ui.api.api_components.keys import KeyManager
from .base import BaseScreen


class HelpWidget(Static):
    """
    Base static widget used by all components on the help screen.

    Provides shared CSS defaults for centering and sizing.
    """

    DEFAULT_CSS = """
    HelpWidget {
        content-align: center middle;
        width: 80%;
        margin: 1;
    }
    """


class Header(HelpWidget):
    """
    Header widget that displays the welcome message at the top of the help screen.
    """

    def render(self) -> RenderableType:
        """Render the welcome message."""
        return "Welcome to Dooit!"


class Outro(HelpWidget):
    """
    Footer widget that displays credits, a GitHub link, and navigation hints
    at the bottom of the help screen.
    """

    COMPONENT_CLASSES = {
        "exit",
        "thanks",
        "github",
    }

    def render(self) -> RenderableType:
        """Render the credits, GitHub link, and escape hint."""
        thanks = Text.from_markup(
            "     Thanks for using Dooit <3",
            style=self.get_component_rich_style("thanks"),
        )
        github = Text.from_markup("You can find this project on  github -> ")
        go_back = Text.from_markup("     Use  escape  to go back")

        go_back.highlight_words(
            [" escape "],
            style=self.get_component_rich_style("exit"),
        )

        github_link = "'https://www.github.com/dooit-org/dooit'"
        github.highlight_words(
            [" github -> "],
            style=Style.from_meta(
                {"@click": f"app.open_url({github_link})"},
            ),
        )

        return Text() + thanks + "\n" + github + "\n\n" + go_back


class DooitKeyTable(HelpWidget):
    """
    Widget that renders a table of all configured keybindings grouped by category.
    """

    DEFAULT_CSS = """
    DooitKeyTable {
        padding: 1 2;
    }
    """

    COMPONENT_CLASSES = {
        "keybind",
        "arrow",
        "description",
        "table-title",
    }
    BORDER_TITLE = "Key Bindings"

    def __init__(self, keybinds: KeyManager, no_op: Callable):
        super().__init__()
        self.keybinds = keybinds
        self.no_op = no_op

    def render(self) -> RenderableType:
        """Render all keybinding groups as styled Rich tables."""
        tables = []

        for group in self.keybinds.groups:
            t = Table.grid(expand=True, padding=(0, 1))
            t_title = Text(group, style=self.get_component_rich_style("table-title"))
            if group:
                t_title.pad(1)

            t.add_column("key")
            t.add_column("arrow")
            t.add_column("description")

            for keybind, func in self.keybinds.get_keybinds_by_group(group):
                if func.description == "<NOP>":
                    continue

                keybind = Text(keybind, style=self.get_component_rich_style("keybind"))
                arrow = Text("->", style=self.get_component_rich_style("arrow"))
                description = (
                    Text(
                        func.description,
                        style=self.get_component_rich_style("description"),
                    )
                    if func
                    else Text("")
                )

                t.add_row(keybind, arrow, description)

            tables.append(t_title)
            tables.append(t)
            t.add_row()  # padding

        return Group(*tables)


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
        """Compose the help screen with header, key table, and outro widgets."""
        yield Header()
        yield DooitKeyTable(self.api.keys, self.api.no_op)
        yield Outro()

    def key_down(self):
        """Scroll the help screen down using the down arrow key."""
        self.scroll_down()

    def key_up(self):
        """Scroll the help screen up using the up arrow key."""
        self.scroll_up()

    def key_j(self):
        """Scroll the help screen down using the j key."""
        self.scroll_down()

    def key_k(self):
        """Scroll the help screen up using the k key."""
        self.scroll_up()
