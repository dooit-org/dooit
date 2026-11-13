import re
from typing import TYPE_CHECKING, Any, Dict, Optional, Union
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import ForeignKey, select, nulls_last
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from .model import DooitModel
from .manager import manager


if TYPE_CHECKING:  # pragma: no cover
    from dooit.api.workspace import Workspace


class Todo(DooitModel):
    # id: Mapped[int] = mapped_column(primary_key=True, default=generate_unique_id)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_index: Mapped[int] = mapped_column(default=-1)
    description: Mapped[str] = mapped_column(default="")
    due: Mapped[Optional[datetime]] = mapped_column(default=None)
    effort: Mapped[int] = mapped_column(default=0)
    recurrence: Mapped[Optional[timedelta]] = mapped_column(default=None)
    urgency: Mapped[int] = mapped_column(default=1)
    pending: Mapped[bool] = mapped_column(default=True)

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
    def sort_options(cls):
        return ["natural"] + super().sort_options()

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
    def siblings(self) -> List["Todo"]:
        if self.parent_workspace:
            return self.parent_workspace.todos

        if self.parent_todo:
            return self.parent_todo.todos

        return []

    def sort_siblings(self, field: str):
        if field == "natural":
            items = sorted(
                self.siblings,
                key=lambda x: (
                    not x.pending,
                    -x.urgency,
                    x.due or datetime.max,
                    x.order_index,
                ),
            )
        elif field != "pending":
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

    def increase_urgency(self) -> None:
        self.urgency += 1
        self.save()

    def decrease_urgency(self) -> None:
        self.urgency -= 1
        self.save()

    def toggle_complete(self) -> None:
        rolls_over = self.pending and self.recurrence is not None
        if rolls_over:
            self.log_completion()

        self.pending = not self.pending
        self.save()

        # the next occurrence starts with its subtasks open again
        if rolls_over:
            for todo in self.todos:
                if not todo.pending and not todo.is_completion_log:
                    todo.pending = True
                    todo.save()

        # finishing the last subtask completes a recurring ancestor, which the
        # update hooks leave to us so it rolls over to its next occurrence;
        # the hooks complete the non-recurring todos in between
        parent = self.parent_todo
        while parent is not None and not self.pending:
            if parent.recurrence is not None:
                subtasks = [t for t in parent.todos if not t.is_completion_log]
                if parent.pending and subtasks and all(not t.pending for t in subtasks):
                    parent.toggle_complete()
                break

            if parent.pending:
                break

            parent = parent.parent_todo

    def log_completion(self) -> None:
        """Record a completed occurrence of a recurring todo as its first child"""

        todo = Todo(
            parent_todo=self,
            description=f"Completed on {datetime.now():%Y-%m-%d}",
            pending=False,
            order_index=0,
        )
        todo.save()

    @property
    def is_completion_log(self) -> bool:
        """Whether this todo is a history entry added by `log_completion`"""

        parent = self.parent_todo
        if parent is None or parent.recurrence is None:
            return False

        return (
            re.fullmatch(r"Completed on \d{4}-\d{2}-\d{2}", self.description)
            is not None
        )

    def is_due_today(self) -> bool:
        if not self.due:
            return False

        return self.due.date() == datetime.today().date()

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
    def clone_from_id(
        id: int,
        order_index: int,
        parent: Optional[Union["Workspace", "Todo"]] = None,
    ) -> "Todo":
        """
        Copy a todo and its subtodos under `parent` (defaults to the original's parent)
        """

        todo = Todo.from_id(str(id))

        # read the whole subtree first, the copy may be placed inside it
        snapshot = todo._snapshot()
        return Todo._from_snapshot(snapshot, parent or todo.parent, order_index)

    def _snapshot(self) -> Dict[str, Any]:
        fields = ["description", "due", "effort", "recurrence", "urgency", "pending"]
        return {
            "attrs": {field: getattr(self, field) for field in fields},
            "todos": [todo._snapshot() for todo in self.todos],
        }

    @staticmethod
    def _from_snapshot(
        snapshot: Dict[str, Any],
        parent: Union["Workspace", "Todo"],
        order_index: int = -1,
    ) -> "Todo":
        todo = Todo(**snapshot["attrs"], order_index=order_index)
        if isinstance(parent, Todo):
            todo.parent_todo = parent
        else:
            todo.parent_workspace = parent
        todo.save()

        for child in snapshot["todos"]:
            Todo._from_snapshot(child, todo)

        return todo
