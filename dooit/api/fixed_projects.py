"""
Projects that are part of the app rather than of the database

A fixed project is always in the projects pane: it cannot be created, renamed,
moved or deleted, and it owns no todos of its own. What it shows is gathered
from the real projects every time it is asked, which is what lets "Today" pull
one day's work out of the whole tree.

Everything the trees and the status bar read off a `Project` is answered here
too, so a fixed project can be handed around in place of a stored one; what
tells them apart is `is_fixed`, and the `icon` each one is drawn with.

To add another one: subclass `FixedProject`, give it a key, a title, an icon
and a `todo_groups`, and register an instance of it below.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select

from .manager import manager
from .project import Project
from .todo import Todo

FIXED_ID_PREFIX = "FixedProject"

# What separates the steps of a project path in a group heading. A chevron
# rather than a slash: the paths sit in prose-like headings, not in a shell
PATH_SEPARATOR = " › "


@dataclass
class TodoGroup:
    """
    A block of todos shown under one heading

    A blank label means the block stands on its own and needs no heading.
    """

    todos: List[Todo]
    label: str = ""


def owning_project(todo: Todo) -> Optional[Project]:
    """
    The project a todo is filed under, however deeply it is nested inside it
    """

    node = todo
    while node.parent_project is None and node.parent_todo is not None:
        node = node.parent_todo

    return node.parent_project


def project_path(project: Project) -> str:
    """
    The project's name, preceded by the names of every project it sits in
    """

    parts = []
    node: Optional[Project] = project

    while node is not None and not node.is_root:
        parts.append(node.description)
        node = node.parent_project

    return PATH_SEPARATOR.join(reversed(parts))


def _project_order() -> Dict[int, int]:
    """
    Where each project falls when the tree is read top to bottom

    Group blocks follow the projects pane rather than an order of their own, so
    that a heading is found where its project is.
    """

    order: Dict[int, int] = {}

    def walk(project: Project) -> None:
        for child in project.projects:
            order[child.id] = len(order)
            walk(child)

    walk(Project._get_or_create_root())
    return order


class FixedProject:
    """
    Base class for the projects that are always there
    """

    key: str = ""
    title: str = ""
    # Drawn in front of the name, where a regular project gets its folder
    icon: str = ""

    is_fixed: bool = True

    # --- the parts of `Project` the trees and the bar read ---

    is_root: bool = False
    order_index: int = -1
    nest_level: int = 0
    parent_project: Optional[Project] = None
    parent: Optional[Project] = None
    projects: List[Project] = []
    total_projects: int = 0

    @property
    def id(self) -> str:
        return self.key

    @property
    def uuid(self) -> str:
        return f"{FIXED_ID_PREFIX}_{self.key}"

    @property
    def description(self) -> str:
        return self.title

    @property
    def todo_groups(self) -> List[TodoGroup]:
        raise NotImplementedError  # pragma: no cover

    @property
    def todos(self) -> List[Todo]:
        return [todo for group in self.todo_groups for todo in group.todos]

    @property
    def total_todos(self) -> int:
        return len(self.todos)

    # A fixed project has no siblings to be shifted among, and nothing about it
    # is stored, so the whole editing side of a model is a no-op here
    def is_first_sibling(self) -> bool:
        return True

    def is_last_sibling(self) -> bool:
        return True

    @property
    def siblings(self) -> List["FixedProject"]:
        return [self]


# How todos are ordered inside a group: the most urgent first, and everything
# nobody prioritized after the lot of them
def _priority_key(todo: Todo):
    return (todo.priority == 0, todo.priority, todo.order_index)


class TodayProject(FixedProject):
    """
    Everything scheduled for today, wherever in the tree it is filed

    The todos keep the columns they have everywhere else; what the day view
    adds is a block per project, so a row can still be placed at a glance.
    """

    key = "today"
    title = "Today"
    icon = "󰃭"

    @staticmethod
    def _scheduled_today() -> List[Todo]:
        start = datetime.combine(date.today(), time.min)
        query = select(Todo).where(
            Todo.scheduled >= start,
            Todo.scheduled < start + timedelta(days=1),
        )

        return list(manager.session.execute(query).scalars().all())

    @property
    def todo_groups(self) -> List[TodoGroup]:
        groups: Dict[int, List[Todo]] = {}
        projects: Dict[int, Project] = {}

        for todo in self._scheduled_today():
            project = owning_project(todo)

            # A todo hanging off nothing has no block to go in
            if project is None:  # pragma: no cover
                continue

            projects[project.id] = project
            groups.setdefault(project.id, []).append(todo)

        order = _project_order()

        return [
            TodoGroup(
                todos=sorted(groups[project_id], key=_priority_key),
                label=project_path(projects[project_id]),
            )
            for project_id in sorted(groups, key=lambda i: order.get(i, 0))
        ]


_FIXED_PROJECTS: List[FixedProject] = []


def register_fixed_project(project: FixedProject) -> FixedProject:
    """
    Puts a fixed project in the pane, under the ones already registered
    """

    _FIXED_PROJECTS.append(project)
    return project


def fixed_projects() -> List[FixedProject]:
    return list(_FIXED_PROJECTS)


def fixed_project_from_key(key: str) -> Optional[FixedProject]:
    for project in _FIXED_PROJECTS:
        if project.key == key:
            return project

    return None


def fixed_project_from_id(_id: str) -> Optional[FixedProject]:
    """
    The fixed project a row id belongs to, or None if the row is a stored one
    """

    if not _id.startswith(f"{FIXED_ID_PREFIX}_"):
        return None

    return fixed_project_from_key(_id[len(FIXED_ID_PREFIX) + 1 :])


TODAY = TodayProject()
register_fixed_project(TODAY)
