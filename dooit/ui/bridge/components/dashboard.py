from textual.app import App

from dooit.config import ScriptField
from dooit.ui.widgets.dashboard import Dashboard

from ._base import ApiComponent


class DashboardManager(ApiComponent):
    def __init__(self, app: App) -> None:
        super().__init__()
        self.app = app
        self.widgets: list[ScriptField] = []

    def set(self, funcs: list[ScriptField]) -> None:
        self.widgets = funcs

    def ui_refresh(self) -> None:
        self.app.query_one(Dashboard).refresh(recompose=True)
