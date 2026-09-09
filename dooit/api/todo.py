from typing import TYPE_CHECKING, Callable, Dict, Literal, Optional, Union
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import ForeignKey, select, nulls_last
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from .model import DooitModel
from .manager import manager


if TYPE_CHECKING:  # pragma: no cover
    from dooit.api.project import Project


# Effort is a rough estimate of how much work a todo is, on a 1-3 scale;
# 0 means no estimate was made
MAX_EFFORT = 3

# Priority runs the other way round: 1 is the most urgent and 3 the least, and
# 0 means none was set. Written down beside the effort scale so that anything
# reading a priority off typed text has one place to ask how far the scale goes
MAX_PRIORITY = 3

# The orders a pane of todos can be read in. Every one of them ends on the
# order the todos were filed in by hand, so the rows a sort has nothing to say
# about — the ones nobody prioritized, or put a date on — keep the order they
# were given rather than being shuffled around by it.
TodoSortModeType = Literal["priority", "due", "scheduled"]


# The most urgent first, and everything unprioritized after the lot of them:
# priority 1 is the top of the scale and 0 means it was never set, so the rows
# without one are pushed past the end rather than sorting ahead of p1
def priority_key(todo: "Todo") -> tuple:
    return (todo.priority == 0, todo.priority, todo.order_index)


# What a date sort does with the rows carrying no date: they go last. A todo
# nobody put a day on is not due at the beginning of time, it is simply not
# something the sort can place.
def _date_key(attr: str) -> Callable[["Todo"], tuple]:
    def key(todo: "Todo") -> tuple:
        value = getattr(todo, attr)
        return (value is None, value or datetime.max, todo.order_index)

    return key


SORT_KEYS: Dict[str, Callable[["Todo"], tuple]] = {
    "priority": priority_key,
    "due": _date_key("due"),
    "scheduled": _date_key("scheduled"),
}


def sort_todos(todos: List["Todo"], mode: Optional[str]) -> List["Todo"]:
    """
    A run of todos in the order the pane reads them in

    No mode — or one nothing is known about — hands the list straight back, in
    the order the todos were filed in.
    """

    key = SORT_KEYS.get(mode or "")

    if key is None:
        return list(todos)

    return sorted(todos, key=key)


class Todo(DooitModel):
    # id: Mapped[int] = mapped_column(primary_key=True, default=generate_unique_id)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_index: Mapped[int] = mapped_column(default=-1)
    description: Mapped[str] = mapped_column(default="")
    due: Mapped[Optional[datetime]] = mapped_column(default=None)
    # The day the todo is planned to be worked on, as opposed to the deadline
    # that `due` sets
    scheduled: Mapped[Optional[datetime]] = mapped_column(default=None)
    effort: Mapped[int] = mapped_column(default=0)
    recurrence: Mapped[Optional[timedelta]] = mapped_column(default=None)
    priority: Mapped[int] = mapped_column(default=0)
    pending: Mapped[bool] = mapped_column(default=True)
    # When the todo was ticked off. Never shown on a row of its own pane: it is
    # what the Completed project orders its rows by, so that the last thing
    # finished is the first thing seen there
    completed_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    # When the todo was moved to the Bin. A binned todo is shown in the Bin
    # project and nowhere else: not in the project it was filed under, and not
    # in any of the fixed projects that gather work up from across the tree
    binned_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    # The path of the project the todo was filed under, written down at the
    # moment that project stopped existing. It is what a todo outliving its
    # project is put back into when it is revived, and what says where it came
    # from while there is nothing left to point at
    origin_path: Mapped[str] = mapped_column(default="")
    # Free text hanging off the todo, edited in a window of its own rather than
    # in the row: the phone number to call, the steps, the reason it is blocked
    note: Mapped[str] = mapped_column(default="")

    # --------------------------------------------------------------
    # ------------------- Relationships ----------------------------
    # --------------------------------------------------------------

    parent_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("project.id")
    )
    parent_project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="todos",
    )

    parent_todo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("todo.id"))
    parent_todo: Mapped[Optional["Todo"]] = relationship(
        "Todo",
        back_populates="todos",
        remote_side=[id],
    )

    # Deleting the task still takes its steps with it, but a step lifted out
    # of it is not thereby deleted: `delete-orphan` here made the `U` key —
    # which takes a step out of the task it is a step of — sometimes delete
    # the step instead of moving it, since a step on its way to a project is
    # briefly attached to neither
    todos: Mapped[List["Todo"]] = relationship(
        "Todo",
        back_populates="parent_todo",
        cascade="all",
        order_by=order_index,
    )

    @validates("recurrence")
    def validate_pending(self, key, value):
        if value is not None:
            self.pending = True

        return value

    @validates("pending")
    def stamp_completion(self, key, value):
        """
        Dates the todo the moment it is ticked off, and undates it when it is
        unticked

        Hung off the field itself rather than off `toggle_complete`, so that
        every way a todo can be finished is stamped: the hooks that carry a
        parent or a child along with it, and the one that bounces a recurring
        todo straight back to pending, all go through here.
        """

        self.completed_at = None if value else datetime.now()

        return value

    @classmethod
    def from_id(cls, _id: str) -> "Todo":
        _id = _id.lstrip("Todo_")
        query = select(Todo).where(Todo.id == _id)
        res = manager.session.execute(query).scalars().first()
        assert res is not None
        return res

    @property
    def parent(self) -> Optional[Union["Project", "Todo"]]:
        """
        Whatever the todo hangs off, or nothing at all

        A todo normally has one or the other. It can have neither: one that
        outlived the project it was filed under keeps nothing but the path it
        came from, and hangs off nothing until it is put back into a project.
        """

        if self.parent_project:
            return self.parent_project

        return self.parent_todo

    @property
    def is_orphan(self) -> bool:
        """
        Whether the project this todo was filed under is gone

        Only a todo nobody is expected to work on right now can be left this
        way: one in the Bin, or one already done and kept in the log.
        """

        return self.parent_project is None and self.parent_todo is None

    @property
    def is_binned(self) -> bool:
        return self.binned_at is not None

    @property
    def descendants(self) -> List["Todo"]:
        """
        Every todo filed under this one, at any depth
        """

        found: List["Todo"] = []

        for child in self.todos:
            found.append(child)
            found.extend(child.descendants)

        return found

    @property
    def has_same_parent_kind(self) -> bool:
        return self.parent_todo is not None

    @property
    def tags(self) -> List[str]:
        return [i for i in self.description.split() if i[0] == "@"]

    @property
    def status(self) -> str:
        if self.is_completed:
            return "completed"

        if self.is_overdue:
            return "overdue"

        return "pending"

    @property
    def total_children(self) -> int:
        """
        Every todo still to be done under this one, counted at every level

        The steps already done are left out: they are still drawn under this
        todo, but what the count is for is how much of the task is left, which
        is what a collapsed row has no other way of saying. A step thrown in
        the Bin is not work left either — it is not drawn here at all.
        """

        return sum(
            1 + todo.total_children
            for todo in self.todos
            if todo.pending and not todo.is_binned
        )

    @property
    def siblings(self) -> List["Todo"]:
        if self.parent_project:
            return self.parent_project.todos

        if self.parent_todo:
            return self.parent_todo.todos

        return []

    def sort_siblings(self, field: str):
        if field != "pending":
            items = (
                self.session.query(Todo)
                .filter_by(
                    parent_project=self.parent_project,
                    parent_todo=self.parent_todo,
                )
                .order_by(nulls_last(getattr(Todo, field).asc()))
                .all()
            )
        else:
            items = sorted(
                self.siblings,
                key=lambda x: (
                    not x.pending,
                    x.due or datetime.max,
                    x.order_index,
                ),
            )

        for index, todo in enumerate(items):
            todo.order_index = index

        manager.commit()

    def add_todo(self) -> "Todo":
        todo = Todo(parent_todo=self)
        todo.save()
        return todo

    def _add_sibling(self) -> "Todo":
        todo = Todo(
            parent_todo=self.parent_todo,
            parent_project=self.parent_project,
            order_index=self.order_index + 1,
        )
        todo.save()
        return todo

    # --------------------------------------------------------------
    # ------------------- Moving between levels --------------------
    # --------------------------------------------------------------

    def _renumber(self, todos: List["Todo"]) -> None:
        """
        Files a run of todos in the order they are handed over

        The whole run is written back rather than just the todo that moved: a
        run built up by hand can have holes in it, or two todos filed at the
        same index, and either would leave the moved todo landing somewhere
        other than where it was put.
        """

        for order, todo in enumerate(todos):
            todo.order_index = order
            self.session.add(todo)

    @property
    def previous_sibling(self) -> Optional["Todo"]:
        """
        The todo filed directly above this one, or None if it opens the run
        """

        if self.is_first_sibling():
            return None

        siblings = self.siblings
        return siblings[siblings.index(self) - 1]

    def indent(self, parent: Optional["Todo"] = None) -> Optional["Todo"]:
        """
        File this todo under the one above it, as a step of it

        It moves under the todo it was sitting beneath, so what it becomes a
        step of is the row above it. Everything already filed under it comes
        along — it is the todo that moves, not the family — and it lands at
        the end of that todo's steps, which is where a step added by hand
        would have gone.

        Which todo that is can be handed over, since a pane being read in an
        order of its own draws its rows in an order the filing does not know
        about; left out, it is the todo filed directly above this one.

        A todo with nothing above it to move under hands back None rather
        than moving anywhere.
        """

        parent = parent or self.previous_sibling

        if parent is None:
            return None

        steps = list(parent.todos)

        self.parent_project = None
        self.parent_todo = parent
        self._renumber(steps + [self])

        self.save()
        return parent

    def unindent(self) -> Optional[Union["Project", "Todo"]]:
        """
        Take this todo out of the task it is a step of

        It lands directly beside that task rather than at the end of the run
        it is joining: a step pulled out of a task belongs with the task it
        was part of, not at the bottom of the project. Its own steps come
        along with it.

        A todo filed straight under a project is already at the top of its
        run, and hands back None.
        """

        parent = self.parent_todo

        if parent is None:
            return None

        grandparent = parent.parent

        # The task this is a step of outlived the project it was filed under,
        # so there is nothing out here to land beside
        if grandparent is None:  # pragma: no cover
            return None

        run = [todo for todo in parent.siblings if todo.id != self.id]
        after = run.index(parent) + 1

        if isinstance(grandparent, Todo):
            self.parent_todo = grandparent
        else:
            self.parent_todo = None
            self.parent_project = grandparent

        self._renumber(run[:after] + [self] + run[after:])

        self.save()
        return grandparent

    # ----------- HELPER FUNCTIONS --------------

    def set_priority(self, priority: int) -> None:
        self.priority = priority
        self.save()

    def set_effort(self, effort: int) -> None:
        self.effort = max(0, min(effort, MAX_EFFORT))
        self.save()

    def toggle_complete(self) -> None:
        self.pending = not self.pending
        self.save()

    def is_due_today(self) -> bool:
        if not self.due:
            return False

        return self.due and self.due.day == datetime.today().day

    @property
    def is_completed(self) -> bool:
        return self.pending == False

    @property
    def is_pending(self) -> bool:
        return self.pending

    @property
    def is_overdue(self) -> bool:
        if not self.due:
            return False

        return self.pending and self.due < datetime.now()

    @classmethod
    def all(cls) -> List["Todo"]:
        query = select(Todo)
        return list(manager.session.execute(query).scalars().all())

    @staticmethod
    def clone_from_id(id: int, order_index: int) -> "Todo":
        todo = Todo.from_id(str(id))
        fields = [
            "description",
            "due",
            "scheduled",
            "effort",
            "recurrence",
            "priority",
            "pending",
            "completed_at",
            "note",
        ]
        attrs = {field: getattr(todo, field) for field in fields}
        attrs.update(
            {
                "parent_project": todo.parent_project,
                "parent_todo": todo.parent_todo,
                "order_index": order_index,
            }
        )
        new_todo = Todo(**attrs)
        new_todo.save()

        # Clone all child todos recursively
        for i, child_todo in enumerate(todo.todos):
            attrs = {field: getattr(child_todo, field) for field in fields}
            attrs["parent_todo"] = new_todo
            child_clone = Todo(**attrs)
            child_clone.save()

            # Recursively clone any nested todos
            for grandchild in child_todo.todos:
                Todo._clone_todo_recursively(grandchild, child_clone)

        return new_todo

    @staticmethod
    def _clone_todo_recursively(source_todo: "Todo", parent_clone: "Todo") -> None:
        fields = [
            "description",
            "due",
            "scheduled",
            "effort",
            "recurrence",
            "priority",
            "pending",
            "completed_at",
            "note",
            "order_index",
        ]
        attrs = {field: getattr(source_todo, field) for field in fields}
        attrs["parent_todo"] = parent_clone
        todo_clone = Todo(**attrs)
        todo_clone.save()

        for child in source_todo.todos:
            Todo._clone_todo_recursively(child, todo_clone)
