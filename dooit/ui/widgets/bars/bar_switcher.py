from typing import Callable, Optional
from textual.await_complete import AwaitComplete
from textual.widget import Widget
from textual.widgets import ContentSwitcher
from dooit.api.model import DooitModel
from dooit.ui.api.events.events import BarNotification
from dooit.ui.widgets.bars._base import BarBase
from .status_bar import StatusBar
from .confirm_bar import ConfirmBar
from .notification_bar import NotificationBar
from .sort_bar import SortBar
from .field_bar import FieldBar


class BarSwitcher(ContentSwitcher):
    DEFAULT_CSS = """
    BarSwitcher {
        height: 1;
        width: 100%;
    }
    """

    @property
    def visible_content(self) -> BarBase:
        content = super().visible_content

        assert isinstance(content, BarBase)
        return content

    @property
    def is_focused(self):
        return self.current != "status_bar" and self.visible_content.focused

    def add_content(
        self, widget: Widget, *, id: Optional[str] = None, set_current: bool = False
    ) -> AwaitComplete:
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

    def switch_to_confirm(self, callback: Callable, message: Optional[str] = None):
        confirm_bar = ConfirmBar(callback, message) if message else ConfirmBar(callback)
        self.add_content(
            widget=confirm_bar,
            id="confirm_bar",
            set_current=True,
        )

    def switch_to_sort(self, model: DooitModel, callback: Callable):
        sort_bar = SortBar(model, callback)
        self.add_content(
            widget=sort_bar,
            id="sort_bar",
            set_current=True,
        )

    def switch_to_field(self, tree, column: str):
        field_bar = FieldBar(tree, column)
        self.add_content(
            widget=field_bar,
            id="field_bar",
            set_current=True,
        )

    def switch_to_notification(self, event: BarNotification):
        notification_bar = NotificationBar(event.message, event.level, event.auto_exit)
        self.add_content(
            widget=notification_bar,
            id="notification_bar",
            set_current=True,
        )

    async def handle_keypress(self, key: str) -> None:
        if self.current != "status_bar":
            await self.visible_content.handle_keypress(key)
