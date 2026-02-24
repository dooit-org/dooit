from typing import TYPE_CHECKING, Callable

from textual.widgets import Static

from ...bridge.events import ModeChanged

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.bridge.dooit_api import DooitAPI
    from dooit.ui.tui import Dooit

    from .bar_switcher import BarSwitcher


class BarBase(Static):
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
        from dooit.ui.tui import Dooit

        app = super().app
        assert isinstance(app, Dooit)
        return app

    @property
    def api(self) -> "DooitAPI":  # pragma: no cover
        return self.app.api

    @property
    def switcher(self) -> "BarSwitcher":
        from .bar_switcher import BarSwitcher

        parent = self.parent
        assert isinstance(parent, BarSwitcher)
        return parent

    async def on_unmount(self):
        self.post_message(ModeChanged("NORMAL"))
        self.switcher.current = "status_bar"

    def perform_action(self, cancel: bool):
        raise NotImplementedError  # pragma: no cover

    def dismiss(self, cancel: bool):
        self.perform_action(cancel)
        self.app.post_message(ModeChanged("NORMAL"))
        self.remove()

    async def handle_keypress(self, key: str) -> None:  # pragma: no cover
        return
