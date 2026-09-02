from typing import TYPE_CHECKING, Optional, Union
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import ForeignKey, select, nulls_last
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from .model import DooitModel
from .manager import manager


if TYPE_CHECKING:  # pragma: no cover
    from dooit.api.workspace import Workspace


# Effort is a rough estimate of how much work a todo is, on a 1-3 scale;
# 0 means no estimate was made
MAX_EFFORT = 3


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
    # Free text hanging off the todo, edited in a window of its own rather than
    # in the row: the phone number to call, the steps, the reason it is blocked
    note: Mapped[str] = mapped_column(default="")

    # --------------------------------------------------------------
    # ------------------- Relationships ----------------------------
    # --------------------------------------------------------------

    parent_workspace_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workspace.id")
    )
    parent_workspace: Mapped[Optional["Workspace"]] = relationship(
        "Workspace",
        back_populates="todos",
    )

    parent_todo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("todo.id"))
    parent_todo: Mapped[Optional["Todo"]] = relationship(
        "Todo",
        back_populates="todos",
        remote_side=[id],
    )

    todos: Mapped[List["Todo"]] = relationship(
        "Todo",
        back_populates="parent_todo",
        cascade="all, delete-orphan",
        order_by=order_index,
    )

    @validates("recurrence")
    def validate_pending(self, key, value):
        if value is not None:
            self.pending = True

        return value

    @classmethod
    def from_id(cls, _id: str) -> "Todo":
        _id = _id.lstrip("Todo_")
        query = select(Todo).where(Todo.id == _id)
        res = manager.session.execute(query).scalars().first()
        assert res is not None
        return res

    @property
    def parent(self) -> Union["Workspace", "Todo"]:
        assert self.parent_workspace or self.parent_todo

        if self.parent_workspace:
            return self.parent_workspace

        assert self.parent_todo is not None

        return self.parent_todo

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
        Every todo nested under this one, counted at every level
        """

        return sum(1 + todo.total_children for todo in self.todos)

    @property
    def siblings(self) -> List["Todo"]:
        if self.parent_workspace:
            return self.parent_workspace.todos

        if self.parent_todo:
            return self.parent_todo.todos

        return []

    def sort_siblings(self, field: str):
        if field != "pending":
            items = (
                self.session.query(Todo)
                .filter_by(
                    parent_workspace=self.parent_workspace,
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
            parent_workspace=self.parent_workspace,
            order_index=self.order_index + 1,
        )
        todo.save()
        return todo

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
            "note",
        ]
        attrs = {field: getattr(todo, field) for field in fields}
        attrs.update(
            {
                "parent_workspace": todo.parent_workspace,
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
            "note",
            "order_index",
        ]
        attrs = {field: getattr(source_todo, field) for field in fields}
        attrs["parent_todo"] = parent_clone
        todo_clone = Todo(**attrs)
        todo_clone.save()

        for child in source_todo.todos:
            Todo._clone_todo_recursively(child, todo_clone)
