from typing import Type
from sqlalchemy.event import listen
from sqlalchemy.orm.attributes import get_history
from textual import events, on
from textual.containers import Container
from textual.widgets import ContentSwitcher
from dooit.api import Todo, Project
from dooit.api.model import DooitModel
from dooit.ui.api.events import (
    DooitEvent,
    ModeChanged,
    ShowConfirm,
    StartSearch,
    StartSort,
    TodoDescriptionChanged,
    TodoDueChanged,
    TodoScheduledChanged,
    TodoEffortChanged,
    TodoRecurrenceChanged,
    TodoStatusChanged,
    TodoPriorityChanged,
    ProjectDescriptionChanged,
    ProjectRemoved,
    ProjectSelected,
    SwitchTab,
    SpawnHelp,
    SpawnNote,
    BarNotification,
)
from dooit.ui.widgets.trees import ProjectsTree, TodosTree
from dooit.ui.widgets import BarSwitcher, Dashboard
from .base import BaseScreen
from .note import NoteScreen


class DualSplit(Container):
    DEFAULT_CSS = """
    DualSplit {
        layout: grid;
        grid-size: 2 1;
        grid-columns: 1fr 3fr;

        & > #project_switcher {
            margin-left: 1;
        }

        & > #todo_switcher {
            margin-right: 1;
        }
    }
    """


class DualSplitLeft(Container):
    pass


class DualSplitRight(Container):
    pass


class MainScreen(BaseScreen):
    DEFAULT_CSS = """
    MainScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 1;
    }
    """

    def compose(self):
        projects_tree = ProjectsTree(Project._get_or_create_root())

        with DualSplit():
            with ContentSwitcher(id="project_switcher", initial=projects_tree.id):
                yield projects_tree

            with ContentSwitcher(initial="dooit-dashboard", id="todo_switcher"):
                yield Dashboard(id="dooit-dashboard")

        yield BarSwitcher()

    async def handle_key(self, event: events.Key) -> bool:
        # NOTE: Investigate why keys are sent to this screen
        if self.app.screen != self:
            return True

        if self.app.bar_switcher.is_focused:
            await self.app.bar_switcher.handle_keypress(event.key)
            return True

        key = self.resolve_key(event)
        await self.api.handle_key(key)
        return True

    @on(BarNotification)
    def show_notification(self, event: BarNotification):
        self.app.bar_switcher.switch_to_notification(event)

    @on(SwitchTab)
    def switch_tab(self, event: SwitchTab) -> None:
        event.stop()
        self.app.action_focus_next()

    @on(SpawnHelp)
    async def spawn_help(self, _: SpawnHelp) -> None:
        self.app.push_screen("help")

    @on(SpawnNote)
    def spawn_note(self, event: SpawnNote) -> None:
        def refresh_row(_) -> None:
            # Only the row that was open needs redrawing, and only its note
            # column can have changed. A full refresh would re-highlight the
            # first node and throw the cursor back to the top of the pane.
            todos_tree = self.api.vars.todos_tree
            if todos_tree:
                todos_tree.update_current_prompt()

        self.app.push_screen(NoteScreen(event.todo), refresh_row)

    @on(StartSearch)
    def start_search(self, event: StartSearch):
        self.app.bar_switcher.switch_to_search(event.callback)
        self.post_message(ModeChanged("SEARCH"))

    @on(StartSort)
    def start_sort(self, event: StartSort):
        self.app.bar_switcher.switch_to_sort(event.model, event.callback)
        self.post_message(ModeChanged("SORT"))

    @on(ShowConfirm)
    def show_confirm(self, event: ShowConfirm):
        self.app.bar_switcher.switch_to_confirm(event.callback)
        self.post_message(ModeChanged("CONFIRM"))

    @on(ProjectRemoved)
    async def project_removed(self, event: ProjectRemoved):
        """
        Drops the pane of a project that is gone

        Nothing highlights the pane back into place when the project it
        belongs to was the last one, so it is swapped for the dashboard rather
        than left showing (and collecting todos for) a deleted project.
        """

        switcher = self.query_one("#todo_switcher", expect_type=ContentSwitcher)
        panes = switcher.query(f"#TodosTree_{event.project.uuid}")

        if not panes:
            return

        pane = panes.first()
        if switcher.current == pane.id:
            switcher.current = "dooit-dashboard"

        await pane.remove()

    @on(ProjectSelected)
    async def project_selected(self, event: ProjectSelected):
        switcher = self.query_one("#todo_switcher", expect_type=ContentSwitcher)
        tree = TodosTree(event.project)

        if not switcher.query(f"#{tree.id}"):
            await switcher.add_content(tree, set_current=True)
        else:
            switcher.current = tree.id

    # SQLAlchemy event listeners

    def _track_field(
        self, table: Type[DooitModel], field: str, event: Type[DooitEvent]
    ) -> None:
        def track(_mapper, _connection, target: Todo):
            history = get_history(target, field)
            if history.has_changes():
                old = history.deleted[0] if history.deleted else ""
                new = history.added[0] if history.added else ""

                if old or new:
                    self.post_message(
                        event(old, new, target),
                    )

        listen(table, "after_update", track)

    def on_mount(self):
        listeners = (
            (Project, "description", ProjectDescriptionChanged),
            (Todo, "description", TodoDescriptionChanged),
            (Todo, "due", TodoDueChanged),
            (Todo, "scheduled", TodoScheduledChanged),
            (Todo, "effort", TodoEffortChanged),
            (Todo, "recurrence", TodoRecurrenceChanged),
            (Todo, "pending", TodoStatusChanged),
            (Todo, "priority", TodoPriorityChanged),
        )

        for table, field, event in listeners:
            self._track_field(table, field, event)
