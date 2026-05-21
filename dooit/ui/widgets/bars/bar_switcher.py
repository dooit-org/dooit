from typing import Callable, Optional
from textual.await_complete import AwaitComplete
from textual.widget import Widget
from textual.widgets import ContentSwitcher
from dooit.api.model import DooitModel
from dooit.ui.api.events.events import BarNotification
from dooit.ui.widgets.bars._base import BarBase
from .status_bar import StatusBar
from .search_bar import SearchBar
from .confirm_bar import ConfirmBar
from .notification_bar import NotificationBar
from .sort_bar import SortBar


class BarSwitcher(ContentSwitcher):
    """
    A content switcher that manages transitions between different bar widgets.

    Handles mounting and switching between the status bar, search bar,
    confirm bar, sort bar, and notification bar.
    """

    DEFAULT_CSS = """
    BarSwitcher {
        height: 1;
        width: 100%;
    }
    """

    @property
    def search_bar(self):
        """Return the SearchBar widget instance."""
        return self.query_one(SearchBar)

    @property
    def visible_content(self) -> BarBase:
        """Return the currently visible bar widget."""
        content = super().visible_content

        assert isinstance(content, BarBase)
        return content

    @property
    def is_focused(self):
        """Return whether the currently visible bar has focus."""
        return self.current != "status_bar" and self.visible_content.focused

    def add_content(
        self, widget: Widget, *, id: Optional[str] = None, set_current: bool = False
    ) -> AwaitComplete:
        """Add a bar widget, removing any existing widget with the same id."""
        try:
            self.query_one(f"#{id}", expect_type=BarBase).remove()
        except Exception as _:
            pass

        return super().add_content(widget, id=id, set_current=set_current)

    async def on_mount(self):
        self.status_bar = StatusBar()
        self.add_content(
            widget=self.status_bar,
            id="status_bar",
            set_current=True,
        )

    def switch_to_search(self, callback: Callable):
        """Switch the bar to display the search bar."""
        search_bar = SearchBar(callback)
        self.add_content(
            widget=search_bar,
            id="search_bar",
            set_current=True,
        )

    def switch_to_confirm(self, callback: Callable):
        """Switch the bar to display the confirmation prompt."""
        confirm_bar = ConfirmBar(callback)
        self.add_content(
            widget=confirm_bar,
            id="confirm_bar",
            set_current=True,
        )

    def switch_to_sort(self, model: DooitModel, callback: Callable):
        """Switch the bar to display the sort options for the given model."""
        sort_bar = SortBar(model, callback)
        self.add_content(
            widget=sort_bar,
            id="sort_bar",
            set_current=True,
        )

    def switch_to_notification(self, event: BarNotification):
        """Switch the bar to display a notification message."""
        notification_bar = NotificationBar(event.message, event.level, event.auto_exit)
        self.add_content(
            widget=notification_bar,
            id="notification_bar",
            set_current=True,
        )

    async def handle_keypress(self, key: str) -> None:
        """Forward a keypress to the currently visible bar widget."""
        if self.current != "status_bar":
            await self.visible_content.handle_keypress(key)
