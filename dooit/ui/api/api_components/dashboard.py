from collections.abc import Callable
from typing import TYPE_CHECKING

from textual.app import App

from dooit.ui.widgets.dashboard import Dashboard

from ._base import ApiComponent

if TYPE_CHECKING:
    from dooit.config.types import ScriptField


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

    def set(self, items: list["ScriptField"]):
        self.app.screen.query_one(Dashboard).items = items
