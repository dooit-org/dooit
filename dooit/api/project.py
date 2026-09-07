from typing import List, Optional, Union
from sqlalchemy import ForeignKey, asc, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..api.todo import Todo
from .model import DooitModel
from .manager import manager

ModelType = Union["Project", "Todo"]
ModelTypeList = Union[List["Project"], List["Todo"]]


class Project(DooitModel):
    # id: Mapped[int] = mapped_column(primary_key=True, default=generate_unique_id)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_index: Mapped[int] = mapped_column(default=-1)
    description: Mapped[str] = mapped_column(default="")
    is_root: Mapped[bool] = mapped_column(default=False)

    # --------------------------------------------------------------
    # ------------------- Relationships ----------------------------
    # --------------------------------------------------------------

    parent_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("project.id"), default=None
    )
    parent_project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="projects",
        remote_side=[id],
    )

    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="parent_project",
        cascade="all",
        order_by="Project.order_index",
    )
    # Deleting the project still takes its todos with it, but a todo lifted
    # out of it is not thereby deleted: that is how a project is thrown away
    # while what was filed in it goes to the Bin instead of going with it
    todos: Mapped[List["Todo"]] = relationship(
        "Todo",
        back_populates="parent_project",
        cascade="all",
        order_by="Todo.order_index",
    )

    @classmethod
    def _get_or_create_root(cls) -> "Project":
        query = select(Project).where(Project.is_root == True)
        root = manager.session.execute(query).scalars().first()

        if root is None:
            root = Project(is_root=True)

        return root

    @classmethod
    def from_id(cls, _id: str) -> "Project":
        _id = _id.lstrip("Project_")
        query = select(Project).where(Project.id == _id)
        res = manager.session.execute(query).scalars().first()
        assert res is not None
        return res

    @property
    def parent(self) -> Optional["Project"]:
        return self.parent_project

    @property
    def has_same_parent_kind(self) -> bool:
        return self.parent is not None

    @property
    def total_todos(self) -> int:
        """
        Every todo still to be done in here, counted at every level.

        Sub projects are walked into but never counted themselves: the number
        says how much work sits in here, not how it is filed away. A completed
        todo has moved to the Completed project and is counted there, so what
        is left is what the project's own pane shows, and what it shows leaves
        out whatever has been thrown in the Bin.
        """

        return sum(project.total_todos for project in self.projects) + sum(
            1 + todo.total_children
            for todo in self.todos
            if todo.pending and not todo.is_binned
        )

    @property
    def total_projects(self) -> int:
        """
        Every project nested under this one, counted at every level
        """

        return sum(1 + project.total_projects for project in self.projects)

    @property
    def siblings(self) -> List["Project"]:
        if not self.parent_project:
            return []

        assert not self.is_root

        return self.parent_project.projects

    def sort_siblings(self, field: str):
        items = (
            self.session.query(Project)
            .filter_by(
                parent_project=self.parent_project,
            )
            .order_by(asc(getattr(Project, field)))
            .all()
        )

        for index, project in enumerate(items):
            project.order_index = index

        manager.commit()

    def add_project(self) -> "Project":
        project = Project(parent_project=self)
        project.save()
        return project

    def add_todo(self) -> "Todo":
        todo = Todo(parent_project=self)
        todo.save()
        return todo

    def _add_sibling(self) -> "Project":
        project = Project(
            parent_project=self.parent_project,
            order_index=self.order_index + 1,
        )
        project.save()
        return project

    def save(self) -> None:
        if not self.parent_project and not self.is_root:
            root = self._get_or_create_root()
            self.parent_project = root

        return super().save()

    @classmethod
    def all(cls) -> List["Project"]:
        query = select(Project).where(Project.is_root == False)
        return list(manager.session.execute(query).scalars().all())

    @staticmethod
    def clone_from_id(id: int, order_index: int) -> "Project":
        project = Project.from_id(str(id))
        fields = ["description"]
        attrs = {field: getattr(project, field) for field in fields}
        attrs["parent_project_id"] = project.parent_project_id
        attrs["order_index"] = order_index

        new_project = Project(**attrs)
        new_project.save()

        # Clone all child projects recursively
        for child_project in project.projects:
            Project._clone_project_recursively(child_project, new_project)

        # Clone all todos
        for todo in project.todos:
            fields = [
                "description",
                "due",
                "scheduled",
                "effort",
                "recurrence",
                "priority",
                "pending",
                "completed_at",
            ]
            attrs = {field: getattr(todo, field) for field in fields}
            attrs["parent_project"] = new_project

            todo_clone = Todo(**attrs)
            todo_clone.save()

            # Clone all child todos
            for child_todo in todo.todos:
                Todo._clone_todo_recursively(child_todo, todo_clone)

        return new_project

    @staticmethod
    def _clone_project_recursively(
        source_project: "Project", parent_clone: "Project"
    ) -> None:
        fields = ["description", "order_index"]
        attrs = {field: getattr(source_project, field) for field in fields}
        attrs["parent_project"] = parent_clone

        project_clone = Project(**attrs)
        project_clone.save()

        # Clone child projects
        for child_project in source_project.projects:
            Project._clone_project_recursively(child_project, project_clone)

        # Clone todos
        for todo in source_project.todos:
            fields = [
                "description",
                "due",
                "scheduled",
                "effort",
                "recurrence",
                "priority",
                "pending",
                "completed_at",
                "order_index",
            ]
            attrs = {field: getattr(todo, field) for field in fields}
            attrs["parent_project"] = project_clone

            todo_clone = Todo(**attrs)
            todo_clone.save()

            # Clone child todos
            for child_todo in todo.todos:
                Todo._clone_todo_recursively(child_todo, todo_clone)
