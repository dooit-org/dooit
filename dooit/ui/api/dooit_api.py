from typing import TYPE_CHECKING
from dooit.ui.api.events import BarNotification, NotificationType
from dooit.ui.api.plug import PluginManager
from dooit.api import COMPLETED, TODAY, UPCOMING
from .events import DooitEvent, GotoFixedProject, SwitchTab, QuitApp
from dooit.ui.widgets import ModelTree
from dooit.ui.widgets.trees import TodosTree
from dooit.utils import CssManager

from .api_components import (
    KeyManager,
    KeyMatchType,
    LayoutManager,
    Formatter,
    BarManager,
    VarManager,
    DashboardManager,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..tui import Dooit


# What each order is called where it is announced. The field names are what
# the columns are titled, but "scheduled" on its own reads as an adjective
# looking for a noun once it is in a sentence.
SORT_LABELS = {
    "priority": "priority",
    "due": "due date",
    "scheduled": "scheduled date",
}


class DooitAPI:
    def __init__(
        self,
        app: "Dooit",
    ) -> None:
        self.app = app
        self.plugin_manager = PluginManager(self, app.config)
        self.css = CssManager()
        self.keys = KeyManager(self.app.get_dooit_mode)
        self.layouts = LayoutManager(self.app)
        self.formatter = Formatter(self)
        self.bar = BarManager(self)
        self.vars = VarManager(self)
        self.dashboard = DashboardManager(self.app)

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

    def paste_as_sibling(self):
        """Add an item described by whatever is on the clipboard"""

        self.focused.paste_as_sibling()

    def switch_focus(self):
        """Switch focus between the project and the todo list"""

        if self.app.bar_switcher.is_focused:
            return

        if w := self.app.focused:
            w.post_message(SwitchTab())

    def focus_projects(self):
        """Move focus to the projects pane"""

        if self.app.bar_switcher.is_focused:
            return

        self.app.project_tree.focus()

    def focus_todos(self):
        """Move focus to the todos pane"""

        if self.app.bar_switcher.is_focused:
            return

        if todos_tree := self.vars.todos_tree:
            todos_tree.focus()

    def goto_fixed_project(self, key: str):
        """Open a fixed project and start on the first of its tasks"""

        if self.app.bar_switcher.is_focused:
            return

        # Posted at the screen rather than at the app: it is the screen that
        # owns both panes, and so the only place that can move between them
        self.app.screen.post_message(GotoFixedProject(key))

    def goto_today(self):
        """Jump to Today and start on the first task scheduled for it"""

        self.goto_fixed_project(TODAY.key)

    def goto_upcoming(self):
        """Jump to Upcoming and start on the first task scheduled ahead"""

        self.goto_fixed_project(UPCOMING.key)

    def goto_completed(self):
        """Jump to Completed and start on the task finished last"""

        self.goto_fixed_project(COMPLETED.key)

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

    def edit_scheduled(self):
        """Start editing the scheduled date of the todo"""
        return self.edit("scheduled")

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

    def set_priority(self, priority: int):
        """Set the priority of the todo (1 is the highest, 0 clears it)"""
        if isinstance(self.focused, TodosTree):
            self.focused.set_priority(priority)

    def set_effort(self, effort: int):
        """Set the effort of the todo (1 is the lightest, 0 clears it)"""
        if isinstance(self.focused, TodosTree):
            self.focused.set_effort(effort)

    def sort_todos(self, mode: str):
        """Order the todos of a project by priority, due date or scheduled date"""

        tree = self.vars.todos_tree

        # The projects pane can be the focused one, and the order still belongs
        # to the todos beside it: there is only ever one pane of them on screen
        if tree is None:
            return

        # A fixed project turns the order down and says so itself, so there is
        # nothing left for this to announce
        if not tree.sort_by(mode):
            return

        # The order is not written anywhere on the pane, and the rows of a
        # project that has no dates on it do not move when it changes, so the
        # bar is what says the key landed
        self.notify(f"Todos sorted by [b]{SORT_LABELS[mode]}[/b]")

    def toggle_row_shading(self):
        """Toggle the shading of alternate rows in the todos pane"""

        self.vars.row_shading = not self.vars.row_shading

        # Every todos pane redraws, not just the focused one: the switcher
        # keeps one per project, and they all share the setting
        self.app.screen.query(TodosTree).refresh()

    def show_note(self):
        """Show and edit the note of the todo"""
        if isinstance(self.focused, TodosTree):
            self.focused.show_note()

    def show_help(self):
        """Show the help screen"""
        self.focused.show_help()
