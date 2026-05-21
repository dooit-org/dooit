from typing import TYPE_CHECKING, Callable
from textual.widgets import Static


from ...api.events import ModeChanged

if TYPE_CHECKING:  # pragma: no cover
    from .bar_switcher import BarSwitcher
    from dooit.ui.tui import Dooit
    from dooit.ui.api.dooit_api import DooitAPI


class BarBase(Static):
    """
    Abstract base class for all bar widgets in the application.

    Provides common functionality for bars displayed at the bottom of the UI,
    including access to the app, API, and bar switcher, as well as shared
    dismiss and action handling logic.
    """

    DEFAULT_CSS = """
    BarBase {
        height: 1;
        width: 100%;
    }
    """

    focused: bool = True

    def __init__(self, callback: Callable = lambda: None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = callback

    @property
    def app(self) -> "Dooit":
        """Return the Dooit application instance."""
        from dooit.ui.tui import Dooit

        app = super().app
        assert isinstance(app, Dooit)
        return app

    @property
    def api(self) -> "DooitAPI":  # pragma: no cover
        """Return the DooitAPI instance from the application."""
        return self.app.api

    @property
    def switcher(self) -> "BarSwitcher":
        """Return the parent BarSwitcher that manages this bar."""
        from .bar_switcher import BarSwitcher

        parent = self.parent
        assert isinstance(parent, BarSwitcher)
        return parent

    async def on_unmount(self):
        self.post_message(ModeChanged("NORMAL"))
        self.switcher.current = "status_bar"

    def perform_action(self, cancel: bool):
        """Execute the bar's action. Subclasses must override this method."""
        raise NotImplementedError  # pragma: no cover

    def dismiss(self, cancel: bool):
        """Dismiss the bar, performing its action and returning to normal mode."""
        self.perform_action(cancel)
        self.app.post_message(ModeChanged("NORMAL"))
        self.remove()

    async def handle_keypress(self, key: str) -> None:  # pragma: no cover
        return
