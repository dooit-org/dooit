from rich.console import RenderableType
from textual.app import ComposeResult
from textual.widgets import Label, Static


class Dashboard(Static):
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

    def compose(self) -> ComposeResult:
        items = self.app.api.dashboard.widgets

        for i in items:
            self.app.notify(str(i))
            yield Label(i._cached)

    def render(self) -> RenderableType:
        return ""
