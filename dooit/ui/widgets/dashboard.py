from rich.console import RenderableType
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Label, Static


class Dashboard(Static):
    """
    A static widget that displays a centered dashboard view
    composed of labeled items.
    """

    DEFAULT_CSS = """
    Dashboard {
        align: center middle;
        content-align: center middle;
        height: 1fr;
    }

    Dashboard > Label {
        width: 100%;
        content-align: center middle;
    }
    """

    items = reactive([], recompose=True)

    def compose(self) -> ComposeResult:
        """Compose the dashboard by yielding a Label for each item."""
        for i in self.items:
            yield Label(i)

    def render(self) -> RenderableType:
        """Render the dashboard widget as an empty string."""
        return ""
