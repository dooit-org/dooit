from typing import TYPE_CHECKING

from ._base import ApiComponent

if TYPE_CHECKING:  # pragma: no cover
    from dooit.config import ScriptField
    from dooit.ui.tui import DooitAPI


class BarManager(ApiComponent):
    def __init__(self, api: "DooitAPI") -> None:
        super().__init__()
        self.api = api
        self.widgets_left = []
        self.widgets_right = []

    def set(self, left: list["ScriptField"], right: list["ScriptField"]):
        self.widgets_left = left
        self.widgets_right = right

    def get(self):
        return self.widgets_left, self.widgets_right

    def ui_refresh(self) -> None:
        self.api.app.bar.refresh()
