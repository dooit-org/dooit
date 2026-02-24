from typing import TYPE_CHECKING

from ._base import ApiComponent

if TYPE_CHECKING:  # pragma: no cover
    from dooit.config.types import ScriptField
    from dooit.ui.tui import DooitAPI


class BarManager(ApiComponent):
    def __init__(self, api: "DooitAPI") -> None:
        super().__init__()
        self.api = api

    def set(self, left: list["ScriptField"], right: list["ScriptField"]):
        self.api.app.bar.set_scripts(left, right)

    def ui_refresh(self) -> None:
        """Re-render the status bar (widgets read __dooit_value on render)."""
        try:
            self.api.app.bar.refresh()
        except Exception:
            pass
