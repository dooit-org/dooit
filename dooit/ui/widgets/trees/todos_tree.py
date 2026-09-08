from functools import partial
from typing import TYPE_CHECKING, List, Optional, Set, Union
from textual import on
from textual.color import Color
from textual.strip import Strip
from textual.style import Style
from textual.widgets.option_list import Option

from dooit.api import (
    Todo,
    Project,
    TodoGroup,
    move_todo_to_bin,
    restore_todo,
    sort_todos,
)
from dooit.api.fixed_projects import PATH_SEPARATOR
from dooit.ui.api.events import BarNotification, SpawnNote, TodoChanged, TodoRemoved
from dooit.ui.api.events.events import TodoSelected
from dooit.utils import blend
from .model_tree import GroupHeading, ModelTree
from ..renderers.todo_renderer import TodoRender
from ._decorators import refresh_tree, require_highlighted_node
from ._render_dict import TodoRenderDict

if TYPE_CHECKING:  # pragma: no cover
    from ...api.api_components.formatters.model_formatters import (
        TodoFormatter,
    )

Model = Union[Todo, Project]

# How far a group heading is pulled towards the background. The block it opens
# has to be found without being read, so the name sits a step below the column
# titles above it and a step above the hairline it runs into
HEADING_FADE = 0.25


class TodosTree(ModelTree[Model, TodoRenderDict]):
    BORDER_TITLE = "TASKS"
    show_header = True
    CHILDREN_ATTR = "todos"

    # How far every other row is pulled from the pane background towards the
    # lighter one behind it. Just enough to keep a row's columns tied together
    # across the width of the pane, and well short of the step the highlight
    # takes, so that the cursor never reads as banding.
    #
    # Only this pane bands its rows: a todo carries columns off to the right
    # that have to be read back to their description, where a project is
    # little more than its name.
    ROW_SHADE = 0.4

    # Whether a row is followed by the todos filed under it. A pane whose rows
    # are whole tasks draws each with its steps under it, as far as it is
    # expanded; one that gathers single todos from all over the tree draws the
    # flat run of rows it collected, since the parents are not on screen.
    show_children = True

    def __init__(self, model: Model) -> None:
        super().__init__(model, TodoRenderDict(self))

        # Indices of the options the banding falls on, worked out block by
        # block as the rows are built
        self._shaded_rows: Set[int] = set()

    @property
    def row_shade(self) -> Color:
        """The background the shaded half of the rows sits on"""

        theme = self.api.vars.theme
        return Color.parse(blend(theme.background1, theme.background2, self.ROW_SHADE))

    @property
    def _body_offset(self) -> int:
        """Index of the first row that is a todo rather than the column header"""

        if self._options and self._options[0].id == self.HEADER_ID:
            return 1

        return 0

    def _is_shaded(self, index: int) -> bool:
        """
        Whether the option at `index` is one of the banded rows

        Worked out while the rows are built rather than off the index, so that
        a heading never counts as a row and every block starts unshaded.
        """

        if not self.api.vars.row_shading:
            return False

        return (index - self._body_offset) in self._shaded_rows

    def _get_option_render(self, option: Option, style: Style) -> List[Strip]:
        """
        Bands the rows, leaving the highlighted one to the cursor

        The shade is dropped for the highlighted row rather than drawn under
        it, so that the cursor is the only background in play wherever it sits,
        and for a row still flashing, which the pane behind this one mixes its
        own background into.
        """

        index = self._option_to_index.get(option)
        flashing = (option.id or "") in self._flashing

        if (
            not flashing
            and index is not None
            and index != self.highlighted
            and self._is_shaded(index)
        ):
            style += Style(background=self.row_shade)

        return super()._get_option_render(option, style)

    # Whether the pane draws the todos that have been thrown away rather than
    # the ones that have not. A binned todo is in the Bin and nowhere else, so
    # every pane shows one side of this or the other, never both at once
    shows_binned = False

    def visible_children(self, model: Model) -> List[Todo]:
        """
        The todos of this model that the pane has a row for

        A task is what moves: a completed todo filed straight under a project
        has gone to the Completed project, is shown there with everything that
        was finished along with it, and comes back here when it is unticked.
        One thrown away has moved to the Bin the same way, and comes back the
        same way.

        A completed step of a task has gone nowhere. It stays under the todo
        it belongs to, ticked off, for as long as there is anything left to do
        in that todo — which is what makes the parent a task in progress
        rather than a row that empties out as it is worked on.
        """

        if isinstance(model, Todo):
            todos = list(model.todos)
        else:
            todos = [todo for todo in model.todos if todo.pending]

        todos = [todo for todo in todos if todo.is_binned == self.shows_binned]

        return sort_todos(todos, self.sort_mode)

    @property
    def sort_mode(self) -> Optional[str]:
        """
        The order this pane reads its rows in, or None to leave them filed

        The steps of a task are ordered the same way the tasks are: a pane is
        read one way down its whole length, or the order it is in stops
        meaning anything halfway down it.
        """

        return self.api.vars.todo_sort

    def sort_by(self, mode: str) -> bool:
        """
        Read the pane in a different order, and say whether it took

        Every todos pane switches, not just this one: the switcher keeps one
        per project, and an order picked here is the order the next project is
        opened in. The cursor stays on the row it was on rather than on the
        place in the pane that row used to be.

        A pane that orders its own rows turns the order down instead, which is
        what the answer is for.
        """

        self.api.vars.todo_sort = mode

        for tree in self.app.screen.query(TodosTree):
            tree._refresh_and_restore_highlight()

        return True

    def _heading_id(self, index: int) -> str:
        return f"dooit-todo-group-{index}"

    def _make_heading(self, label: str, space_above: bool) -> GroupHeading:
        theme = self.api.vars.theme

        return GroupHeading(
            label=label,
            label_style=blend(theme.foreground1, theme.background1, HEADING_FADE),
            rule_style=theme.background3,
            space_above=space_above,
        )

    @property
    def todo_groups(self) -> List[TodoGroup]:
        """
        The blocks of rows the pane draws

        A project shows the whole of the work filed under it, not just the part
        of it that stopped at this level: its own todos open the pane, and
        everything belonging to a project nested inside it follows in a block
        per project. Otherwise a project that has been split into sub projects
        reads as empty, and the work has to be hunted down a level at a time.

        A project with nothing under it is one unlabelled block, which is a
        plain list of rows: the heading is what marks a block off from the one
        before it, and the first block of a pane has nothing to be marked off
        from.
        """

        groups = [TodoGroup(todos=self.visible_children(self.model))]

        if isinstance(self.model, Project):
            groups.extend(self._sub_project_groups(self.model))

        # A project nobody has filed anything under yet is not a block, it is
        # a heading with nothing beneath it
        return [group for group in groups if group.todos]

    def _sub_project_groups(self, project: Project) -> List[TodoGroup]:
        """
        A block for every project nested under this one, however deep

        Read top to bottom the way the projects pane is, so a block is found
        where its project is over there. A block deeper than a child is headed
        by its path down from here rather than by its name alone, which is
        what keeps two sub projects that were given the same name apart.
        """

        groups: List[TodoGroup] = []

        def walk(parent: Project, prefix: str) -> None:
            for child in parent.projects:
                label = f"{prefix}{child.description}"
                groups.append(
                    TodoGroup(todos=self.visible_children(child), label=label)
                )
                walk(child, f"{label}{PATH_SEPARATOR}")

        walk(project, "")
        return groups

    def _body_options(self) -> List[Option]:
        """
        Every block of the pane, each under the name it belongs to
        """

        options: List[Option] = []
        self._shaded_rows = set()

        for index, group in enumerate(self.todo_groups):
            if group.label:
                options.append(
                    self.static_row(
                        self._heading_id(index),
                        partial(self._make_heading, group.label, bool(index)),
                    )
                )

            for row, todo in enumerate(self._group_rows(group.todos)):
                if row % 2:
                    self._shaded_rows.add(len(options))

                options.append(Option("", id=self._renderers[todo.uuid].id))

        return options

    def _group_rows(self, todos: List[Todo]) -> List[Todo]:
        """
        The rows a block draws, in the order they are drawn in

        The todos the block gathered, each followed by whatever is filed under
        it for a pane that shows them, exactly as far as the node is expanded.
        """

        if not self.show_children:
            return list(todos)

        rows: List[Todo] = []

        for todo in todos:
            rows.append(todo)

            if self.is_node_expaned(todo.uuid):
                rows.extend(self._group_rows(self.visible_children(todo)))

        return rows

    def _get_parent(self, id: str) -> Optional[Todo]:
        return Todo.from_id(id).parent_todo

    def is_node_expaned(self, _id: str) -> bool:
        return super().is_node_expaned(_id) or self.api.vars.always_expand_todos

    @property
    def formatter(self) -> "TodoFormatter":
        return self.api.formatter.todos

    @property
    def render_layout(self):
        return self.api.layouts.todo_layout

    def add_todo(self) -> str:
        todo = self.model.add_todo()
        render = TodoRender(todo, tree=self)
        self.add_option(Option(render.prompt, id=render.id))
        return todo.uuid

    def _add_first_item(self) -> Todo:
        return self.model.add_todo()

    def _create_child_node(self) -> Todo:
        return self.current_model.add_todo()

    def _delete_current_model(self) -> None:
        assert isinstance(self.current_model, Todo)
        self.post_message(TodoRemoved(self.current_model))

        return super()._delete_current_model()

    def _bin_node(self) -> None:
        """
        Throws the highlighted task away, with everything filed under it

        Nothing is lost by it: the task is in the Bin from here on, where it
        can be looked at, put back, or dropped for good. Which is why the key
        never asks first.
        """

        todo = self.current_model
        assert isinstance(todo, Todo)

        if todo.is_binned:
            self._already_binned()
            return

        move_todo_to_bin(todo)
        self.post_message(TodoChanged(todo))

    def _already_binned(self) -> None:
        self.post_message(
            BarNotification(
                "Already in the Bin — [b]yy[/b] deletes it for good", "warning"
            )
        )

    def _restore_node(self) -> None:
        """
        Takes the highlighted task back out of the Bin
        """

        todo = self.current_model
        assert isinstance(todo, Todo)

        if not todo.is_binned:
            self.post_message(
                BarNotification("Only tasks in the Bin can be restored", "warning")
            )
            return

        revived = restore_todo(todo)
        self.post_message(TodoChanged(todo))
        self.announce_revived(revived)

    def announce_revived(self, projects: List[Project]) -> None:
        """
        Points out the projects that had to be rebuilt to take a task back

        A task coming back out of the Bin or off the completion log lands
        wherever it was filed, which can be a project nobody kept. It is built
        again out of the name the task was carrying, and the projects pane
        flashes it the same way this one flashes a recurring todo: the row it
        appeared in is the only thing that says the key did anything at all.
        """

        if not projects:
            return

        tree = self.api.vars.projects_tree

        for project in projects:
            parent = project.parent_project

            # A project rebuilt inside another one is only reachable if what it
            # sits in is open, and what it sits in may have just been built too
            if parent is not None and not parent.is_root:
                tree.expanded_nodes[parent.uuid] = True

        tree.force_refresh()

        for project in projects:
            tree.flash_row(project.uuid)

        self.post_message(
            BarNotification(f"Brought back [b]{projects[-1].description}[/b]", "info")
        )

    def _row_above(self, todo: Todo) -> Optional[Todo]:
        """
        The task drawn directly above this one, out of the ones beside it

        Read off the pane rather than off the filing: a pane being read by
        priority or by date draws the run in an order of its own, and the row
        a key talks about is the row that is there to be seen.
        """

        parent = todo.parent

        if parent is None:  # pragma: no cover
            return None

        siblings = self.visible_children(parent)

        if todo not in siblings:  # pragma: no cover
            return None

        index = siblings.index(todo)

        return siblings[index - 1] if index else None

    @require_highlighted_node
    def indent_node(self) -> None:
        """
        Makes the highlighted task a step of the task above it

        The task it moves under is opened by the same key, so the row is
        still there to be worked on rather than folded away out of sight the
        moment it moves.
        """

        todo = self.current_model
        assert isinstance(todo, Todo)

        parent = self._row_above(todo)

        if parent is None:
            self.post_message(
                BarNotification("Nothing above this to make it a step of", "warning")
            )
            return

        todo.indent(parent)

        # Expanding refreshes the pane, which is what puts the row where it
        # has just been filed; the cursor is carried onto it from there
        self._expand_node(parent.uuid)
        self.post_message(TodoChanged(todo))

    @require_highlighted_node
    @refresh_tree
    def unindent_node(self) -> None:
        """
        Takes the highlighted task out of the task it is a step of
        """

        todo = self.current_model
        assert isinstance(todo, Todo)

        if todo.unindent() is None:
            self.post_message(
                BarNotification("This task is not a step of anything", "warning")
            )
            return

        self.post_message(TodoChanged(todo))

    def toggle_complete(self):
        todo = self.current_model
        assert isinstance(todo, Todo)

        was_scheduled_for = todo.scheduled

        todo.toggle_complete()
        self.refresh_options()

        # A recurring todo is handed back pending with its next date already
        # set, so the only thing the tick changed is the day it is planned for:
        # the flash is what says so. Every other row says it for itself, by
        # moving out of the pane.
        if todo.scheduled != was_scheduled_for:
            self.flash_row(todo.uuid)

    def set_priority(self, priority: int):
        assert isinstance(self.current_model, Todo)

        self.current_model.set_priority(priority)
        self.update_current_prompt()

    def set_effort(self, effort: int):
        assert isinstance(self.current_model, Todo)

        self.current_model.set_effort(effort)
        self.update_current_prompt()

    def show_note(self):
        assert isinstance(self.current_model, Todo)

        # Posted rather than pushed from here: the screen package imports the
        # trees, so reaching the other way would close the circle
        self.post_message(SpawnNote(self.current_model))

    @on(ModelTree.OptionHighlighted)
    def todo_highlighted(self, event: ModelTree.OptionHighlighted):
        assert event.option_id

        event.stop()

        if self.is_static_row(event.option_id):
            return

        self.post_message(TodoSelected(Todo.from_id(event.option_id)))
