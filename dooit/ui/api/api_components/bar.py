from typing import TYPE_CHECKING, List
from dooit.ui.widgets.bars import StatusBarWidget
from ._base import ApiComponent

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.tui import DooitAPI


class BarManager(ApiComponent):
    """
    Manages the status bar widgets displayed in the Dooit application.
    Provides methods to configure which widgets appear in the status bar.
    """

    def __init__(self, api: "DooitAPI") -> None:
        super().__init__()
        self.api = api

    def set(self, widgets: List[StatusBarWidget]):
        """Set the status bar widgets, registering their functions with the plugin manager."""
        for widget in widgets:
            self.api.plugin_manager.register(widget.func)

        self.api.app.bar.set_widgets(widgets)
