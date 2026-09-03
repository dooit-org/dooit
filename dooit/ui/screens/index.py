from typing import Type
from sqlalchemy.event import listen
from sqlalchemy.orm.attributes import get_history
from textual import events, on
from textual.containers import Container
from textual.widgets import ContentSwitcher
from dooit.api import TODAY, Todo, Project, fixed_project_from_key
from dooit.api.model import DooitModel
from dooit.ui.api.events import (
    DooitEvent,
    ModeChanged,
    ShowConfirm,
    StartFieldEdit,
    StartSearch,
    StartSort,
    TodoChanged,
    TodoDescriptionChanged,
    TodoDueChanged,
    TodoNoteChanged,
    TodoScheduledChanged,
    TodoEffortChanged,
    TodoRecurrenceChanged,
    TodoStatusChanged,
    TodoPriorityChanged,
    ProjectChanged,
    ProjectDescriptionChanged,
    ProjectRemoved,
    ProjectSelected,
    GotoFixedProject,
    SwitchTab,
    SpawnHelp,
    SpawnNote,
    BarNotification,
)
from dooit.ui.widgets.trees import ProjectsTree, TodosTree, make_todos_tree
from dooit.ui.widgets import BarSwitcher, Dashboard, ModelTree
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

        # Every key on this screen is dooit's own. Stopping it here is what
        # keeps it away from the bindings textual keeps at the app level --
        # ctrl+c among them, which is bound to a "press ctrl+q to quit" notice
        # that would otherwise turn up on top of the copy it just did
        event.stop()

        key = self.resolve_key(event)

        # Resolved on the way in rather than per bar: a bar that is typed into
        # wants the character that was pressed, not the name of the key
        if self.app.bar_switcher.is_focused:
            await self.app.bar_switcher.handle_keypress(key)
            return True

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
        self.app.push_screen(NoteScreen(event.todo))

    @on(StartSearch)
    def start_search(self, event: StartSearch):
        self.app.bar_switcher.switch_to_search(event.callback)
        self.post_message(ModeChanged("SEARCH"))

    @on(StartFieldEdit)
    def start_field_edit(self, event: StartFieldEdit):
        self.app.bar_switcher.switch_to_field(event.tree, event.column)

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

    async def show_project(self, project) -> TodosTree:
        """
        Brings the project's tasks pane to the front, building it if need be
        """

        switcher = self.query_one("#todo_switcher", expect_type=ContentSwitcher)
        tree = make_todos_tree(project)

        existing = switcher.query(f"#{tree.id}")
        if not existing:
            await switcher.add_content(tree, set_current=True)
            return tree

        switcher.current = tree.id
        return existing.first(TodosTree)

    @on(ProjectSelected)
    async def project_selected(self, event: ProjectSelected):
        await self.show_project(event.project)

    @on(GotoFixedProject)
    async def goto_fixed_project(self, event: GotoFixedProject) -> None:
        """
        Moves onto a fixed project and hands the focus to its first task

        The pane is brought up here rather than left to the `ProjectSelected`
        the highlight sends off, so that there is something to focus by the
        time the cursor is put on the first todo.
        """

        project = fixed_project_from_key(event.key)
        if project is None:  # pragma: no cover
            return

        self.api.vars.projects_tree.highlight_id(project.uuid)

        tree = await self.show_project(project)
        tree.focus()
        tree.action_first()

    @on(TodoChanged)
    @on(ProjectChanged)
    def model_changed(self, _: DooitEvent) -> None:
        """
        Redraws every pane once something has actually changed

        A todo is no longer in one place only: it is in the pane of the project
        it is filed under, and in every fixed project that gathered it up. A
        pane that is not in front goes on drawing whatever it was built with,
        so an edit made in one of them would leave the others saying the old
        thing until they happened to be rebuilt. All of them are refreshed
        together, which also settles what a fixed project shows and in what
        order, neither of which the edited row alone can say.

        Only the events that write a model back come through here; the ones
        that say where the cursor is do not, or this would run per keystroke.
        """

        for tree in self.query(ModelTree):
            tree.force_refresh()

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
        # Dooit opens on the day's work: the tasks scheduled for today, with
        # the cursor already on the first of them. Left until after the first
        # refresh, so that the config has had its say about the panes first.
        self.call_after_refresh(
            lambda: self.post_message(GotoFixedProject(TODAY.key))
        )

        listeners = (
            (Project, "description", ProjectDescriptionChanged),
            (Todo, "description", TodoDescriptionChanged),
            (Todo, "due", TodoDueChanged),
            (Todo, "scheduled", TodoScheduledChanged),
            (Todo, "effort", TodoEffortChanged),
            (Todo, "recurrence", TodoRecurrenceChanged),
            (Todo, "pending", TodoStatusChanged),
            (Todo, "priority", TodoPriorityChanged),
            (Todo, "note", TodoNoteChanged),
        )

        for table, field, event in listeners:
            self._track_field(table, field, event)
