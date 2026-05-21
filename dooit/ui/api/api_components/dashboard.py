from typing import List

from rich.text import TextType
from textual.app import App

from dooit.ui.widgets.dashboard import Dashboard
from ._base import ApiComponent


class DashboardManager(ApiComponent):
    """
    Manages the dashboard content displayed in the Dooit application.
    Provides methods to configure the items shown on the dashboard screen.
    """

    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app

    def set(self, items: List[TextType]):
        """Set the dashboard display items."""
        self.app.screen.query_one(Dashboard).items = items
