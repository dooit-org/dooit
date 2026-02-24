from typing import TYPE_CHECKING

from dooit.config.config import AppConfig
from dooit.config.reader import ConfigReader
from dooit.ui.bridge.events import BarNotification, NotificationType
from dooit.ui.widgets import ModelTree
from dooit.ui.widgets.trees import TodosTree
from dooit.utils.css_manager import CssManager

from .components import (
    BarManager,
    DashboardManager,
    Formatter,
    KeyManager,
    KeyMatchType,
    LayoutManager,
    VarManager,
)
from .events import DooitEvent, QuitApp, SwitchTab

if TYPE_CHECKING:  # pragma: no cover
    from ..tui import Dooit


class DooitAPI:
    def __init__(
        self,
        app: "Dooit",
    ) -> None:
        self.app = app
        self.load_config()

    def load_config(self):
        """Load and apply configuration from base defaults and user overrides."""
        config = ConfigReader()
        config.load_defaults()
        config = AppConfig.from_resolved(config)

        self.css = CssManager.from_config(config)
        self.keys = KeyManager.from_config(self, config, self.app.get_dooit_mode)
        self.layouts = LayoutManager.from_config(config)
        self.formatter = Formatter.from_config(config)
        self.bar = BarManager.from_config(config)
        self.vars = VarManager.from_config(config, self)
        self.dashboard = DashboardManager.from_config(config)

        # reload_targets = {}
        # self.refresh_service = RefreshService(scripts, reload_targets)

        self.css.refresh_css()

    def no_op(self):
        """<NOP>"""
        pass

    def quit(self):
        """Quit dooit"""
        self.app.post_message(QuitApp())

    def notify(self, message: str, level: NotificationType = "info") -> None:
        self.app.bar_switcher.switch_to_notification(BarNotification(message, level))

    async def handle_key(self, key: str) -> None:
        keymatch = self.keys.register_key(key)

        if keymatch.match_type == KeyMatchType.NoMatchFound:
            await self.focused.handle_keypress(key)
            return

        if keymatch.match_type == KeyMatchType.MultipleMatchFound:
            return

        assert keymatch.function is not None
        try:
            keymatch.function.callback()
        except Exception as e:
            self.app.bar_switcher.switch_to_notification(
                BarNotification(str(e), "error")
            )

    def trigger_event(self, event: DooitEvent):
        return
        self.plugin_manager.on_event(event)

    # -----------------------------------------

    @property
    def focused(self) -> ModelTree:
        focused = self.app.focused
        if isinstance(focused, ModelTree):
            return focused

        raise ValueError(f"Expected BaseTree, got {type(focused)}")

    def copy_description_to_clipboard(self):
        """Copy the description of the focused item to the clipboard"""

        self.focused.copy_description_to_clipboard()

    def copy_model(self):
        """Copy the current highlighted node to clipboard"""
        self.focused.copy_model_to_clipboard()

    def paste_model_above(self):
        """Paste the copied node in the list (puts above the highlighted)"""
        self.focused.paste_model_from_clipboard("above")

    def paste_model_below(self):
        """Paste the copied node in the list (puts below the highlighted)"""
        self.focused.paste_model_from_clipboard("below")

    def switch_focus(self):
        """Switch focus between the workspace and the todo list"""

        if self.app.bar_switcher.is_focused:
            return

        if w := self.app.focused:
            w.post_message(SwitchTab())

    def move_down(self):
        """Move the cursor down in the focused list"""

        self.focused.action_cursor_down()

    def move_up(self):
        """Move the cursor up in the focused list"""

        self.focused.action_cursor_up()

    def shift_up(self):
        """Shift the highlighted item up"""

        self.focused.shift_up()

    def shift_down(self):
        """Shift the highlighted item down"""

        self.focused.shift_down()

    def go_to_top(self):
        """Move the cursor to the top of the list"""
        self.focused.action_first()

    def go_to_bottom(self):
        """Move the cursor to the bottom of the list"""
        self.focused.action_last()

    def edit(self, property: str):
        """Start editing a property of the focused item"""
        self.focused.start_edit(property)

    def edit_description(self):
        """Start editing the description of the focused item"""
        return self.edit("description")

    def edit_due(self):
        """Start editing the due date of the todo"""
        return self.edit("due")

    def edit_recurrence(self):
        """Start editing the recurrence of the todo"""
        return self.edit("recurrence")

    def edit_effort(self):
        """Start editing the effort of the todo"""
        return self.edit("effort")

    def add_sibling(self):
        """Add a sibling to highlighted item"""
        self.focused.add_sibling()

    def toggle_expand(self):
        """Toggle the expansion of the highlighted item"""
        self.focused.toggle_expand()

    def toggle_expand_parent(self):
        """Toggle the expansion of the parent of the highlighted item"""
        self.focused.toggle_expand_parent()

    def add_child_node(self):
        """Add a child to the highlighted item"""
        self.focused.add_child_node()

    def remove_node(self):
        """Remove the highlighted item"""
        self.focused.remove_node()

    def start_search(self):
        """Start a search within the list"""
        self.focused.start_search()

    def start_sort(self):
        """Start sorting the siblings of the highlighted item"""
        self.focused.start_sort()

    def toggle_complete(self):
        """Toggle the completion of the todo"""
        if isinstance(self.focused, TodosTree):
            self.focused.toggle_complete()

    def increase_urgency(self):
        """Increase the urgency of the todo"""
        if isinstance(self.focused, TodosTree):
            self.focused.increase_urgency()

    def decrease_urgency(self):
        """Decrease the urgency of the todo"""
        if isinstance(self.focused, TodosTree):
            self.focused.decrease_urgency()

    def show_help(self):
        """Show the help screen"""
        self.focused.show_help()
