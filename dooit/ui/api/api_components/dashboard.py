from collections.abc import Callable
from typing import List

from rich.text import TextType
from textual.app import App

from dooit.ui.widgets.dashboard import Dashboard
from ._base import ApiComponent


class DashboardManager(ApiComponent):
    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self._widget_funcs: list[Callable] = []

    def set_widget_funcs(self, funcs: list[Callable]) -> None:
        """Store the script wrapper functions for dashboard widgets."""
        self._widget_funcs = funcs

    def ui_refresh(self) -> None:
        """Re-read __dooit_value from each widget func and update the dashboard."""
        items = []
        for func in self._widget_funcs:
            value = getattr(func, "__dooit_value", "")
            items.append(value)
        self.set(items)

    def set(self, items: List[TextType]):
        self.app.screen.query_one(Dashboard).items = items
