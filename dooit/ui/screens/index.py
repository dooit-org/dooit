from typing import Optional, Type
from rich.markup import escape
from sqlalchemy.event import listen
from sqlalchemy.orm.attributes import get_history
from textual import events, on
from textual.containers import Container
from textual.widgets import ContentSwitcher
from dooit.api import BIN, COMPLETED, TODAY, Todo, Project, fixed_project_from_key
from dooit.api.model import DooitModel
from dooit.ui.api.events import (
    DooitEvent,
    ModeChanged,
    ShowConfirm,
    StartFieldEdit,
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
    SpawnQuickAdd,
    SpawnSearch,
    BarNotification,
)
from dooit.api.fixed_projects import owning_project
from dooit.ui.api.events.events import ProjectType
from dooit.ui.widgets.trees import ProjectsTree, TodosTree, make_todos_tree
from dooit.ui.widgets import BarSwitcher, Dashboard, ModelTree
from .base import BaseScreen
from .note import NoteScreen
from .quick_add import QuickAdded, QuickAddScreen
from .search import SearchScreen, task_root


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

    @on(SpawnQuickAdd)
    def spawn_quick_add(self, _: SpawnQuickAdd) -> None:
        """
        Opens the one line task entry over the app

        The project the line falls back to is worked out here rather than
        inside the overlay: once the overlay is up it is the screen, and the
        panes it would have to ask are behind it.
        """

        project = self.api.vars.current_project

        self.app.push_screen(
            QuickAddScreen(project if isinstance(project, Project) else None),
            self.quick_add_done,
        )

    def quick_add_done(self, result: Optional[QuickAdded]) -> None:
        """
        Redraws the panes around a task that was added from somewhere else

        The task can have landed in a project nobody is looking at, so the bar
        says where it went: the row itself may be nowhere on screen.
        """

        if result is None:
            return

        todo = result.todo
        project = todo.parent_project

        if result.project_created and project is not None:
            self.reveal_project(project)

        self.post_message(TodoChanged(todo))

        where = escape(project.description) if project else ""
        what = escape(todo.description)
        into = "to new project" if result.project_created else "to"

        self.post_message(
            BarNotification(f"Added [b]{what}[/b] {into} [b]{where}[/b]", "info")
        )

    def reveal_project(self, project: Project) -> None:
        """
        Brings a project that has just been built into view, and flashes it

        The same thing that happens to a project rebuilt to take a task back
        out of the Bin: a new row appears among ones that were already there,
        and the flash is what says which of them is the new one. A project
        made inside another is only reachable once that one is open, so its
        parents are expanded before the pane is redrawn.
        """

        tree = self.api.vars.projects_tree
        parent = project.parent_project

        while parent is not None and not parent.is_root:
            tree.expanded_nodes[parent.uuid] = True
            parent = parent.parent_project

        tree.force_refresh()
        tree.flash_row(project.uuid)

    @on(SpawnSearch)
    def spawn_search(self, _: SpawnSearch) -> None:
        self.app.push_screen(SearchScreen(), self.search_done)

    async def search_done(self, todo: Optional[Todo]) -> None:
        if todo is not None:
            await self.reveal_todo(todo)

    async def reveal_todo(self, todo: Todo) -> None:
        """
        Puts the cursor on a task that was found from somewhere else

        The task can be anywhere: inside a project nobody has opened, under a
        project that is not even unfolded, filed as a step of another task. So
        the way down to it is opened a level at a time -- the projects above
        it in the left hand pane, the tasks above it in the right hand one --
        before the row can be pointed at.

        The projects pane is moved onto the project first. It re-emits
        `ProjectSelected` whenever it is redrawn, and a pane left highlighting
        something else would take the tasks pane back to it the moment
        anything changed.
        """

        project = self.pane_of(todo)

        if project is None:  # pragma: no cover
            return

        projects_tree = self.api.vars.projects_tree
        parent = project.parent_project

        while parent is not None and not parent.is_root:
            projects_tree.expanded_nodes[parent.uuid] = True
            parent = parent.parent_project

        projects_tree.force_refresh()
        projects_tree.highlight_id_if_shown(project.uuid)

        tree = await self.show_project(project)

        step = todo.parent_todo
        while step is not None:
            tree.expanded_nodes[step.uuid] = True
            step = step.parent_todo

        tree.force_refresh()
        self.app.set_focus(tree)

        # After the focus, which puts the cursor on the first row of a pane
        # that had none; and the flash last, so the row says which of them was
        # the one that was asked for
        self.point_at(tree, todo)

    @staticmethod
    def pane_of(todo: Todo) -> Optional[ProjectType]:
        """
        The pane a task is to be found in

        Its own project while there is work left in it. A task that is over
        with has left that pane for one of the fixed ones -- finished for
        Completed, thrown away for the Bin -- and is only drawn there.
        """

        if todo.is_binned:
            return BIN

        if not task_root(todo).pending:
            return COMPLETED

        return owning_project(todo)

    @staticmethod
    def point_at(tree: TodosTree, todo: Todo) -> None:
        """
        Puts the cursor on a task, or on the nearest thing to it that is drawn

        A pane need not have a row for the task itself: the fixed ones gather
        whole tasks, and a step of one is only in there inside its parent. The
        parent is where the cursor stops in that case, which is as close to
        the step as that pane goes.
        """

        node: Optional[Todo] = todo

        while node is not None:
            if tree.highlight_id_if_shown(node.uuid):
                tree.flash_row(node.uuid)
                return

            node = node.parent_todo

    @on(StartFieldEdit)
    def start_field_edit(self, event: StartFieldEdit):
        self.app.bar_switcher.switch_to_field(event.tree, event.column)

    @on(StartSort)
    def start_sort(self, event: StartSort):
        self.app.bar_switcher.switch_to_sort(event.model, event.callback)
        self.post_message(ModeChanged("SORT"))

    @on(ShowConfirm)
    def show_confirm(self, event: ShowConfirm):
        self.app.bar_switcher.switch_to_confirm(event.callback, event.message)
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
