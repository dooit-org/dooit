"""
Throwing work away, and getting it back

Nothing in dooit is deleted by accident. A todo that is dropped goes to the
Bin, where it stays, whole, until it is either restored or deleted for good;
the only things that actually remove a row are the keys that ask first — the
one that deletes what the cursor is on, and the one that empties the Bin out.

Dropping a project is the same thing one level up: everything filed under it
goes to the Bin carrying the path it came from, and the project row itself is
the only part that goes. That path is what a todo is put back into when it is
revived — the project is built again out of its own name if nobody kept it, so
restoring something never quietly drops it somewhere else.
"""

from datetime import datetime
from typing import Iterator, List, Optional

from .fixed_projects import PATH_SEPARATOR, binned_tasks, project_path
from .manager import manager
from .project import Project
from .todo import Todo

# What a project rebuilt to hold a revived todo is called: its own name, with
# this in front of it. The project is not the one that was there before — it
# has none of what was filed in it besides the row that brought it back — and
# the prefix is what says so without the name having to be typed again.
REVIVED_PREFIX = "revived - "

# The name a revived project falls back on when the todo carries no path at
# all: something has to be there to put it in, and an empty name is not a
# project
UNKNOWN_PROJECT = "recovered"


def _sub_projects(project: Project) -> Iterator[Project]:
    """
    Every project nested under this one, at any depth
    """

    for child in project.projects:
        yield child
        yield from _sub_projects(child)


def _family(todo: Todo) -> List[Todo]:
    """
    The todo and every step filed under it, at any depth
    """

    return [todo, *todo.descendants]


def move_todo_to_bin(todo: Todo) -> None:
    """
    Throws a todo away, with everything filed under it

    A task goes in whole: its steps are part of it, not rows that happen to be
    beneath it, and a Bin holding half a task is a Bin nothing can be restored
    out of. The one stamp over the family is what keeps them together in the
    pane, which reads by the moment things were thrown away.
    """

    stamp = datetime.now()

    for node in _family(todo):
        node.binned_at = stamp

    todo.save()


def restore_todo(todo: Todo) -> List[Project]:
    """
    Takes a todo back out of the Bin, and says which projects that rebuilt

    The family comes out together, the way it went in. Anything still to be
    done needs somewhere to be done in, so a todo that outlived its project
    gets it back here; one that is already finished has the completion log to
    live in and is left as it is until it is unticked.
    """

    for node in _family(todo):
        node.binned_at = None

    todo.save()

    if todo.pending:
        return revive_home(todo)

    return []


def revive_home(todo: Todo) -> List[Project]:
    """
    Files a todo that outlived its project back into one

    The path it was carrying is walked from the top of the tree down, and
    whatever is missing along the way is built: a project that is still there
    takes the todo straight back, and one that is gone comes back under its
    own name with `revived - ` in front of it.

    What comes back is the list of projects that had to be made, so that the
    pane which is about to redraw can point them out.
    """

    if not todo.is_orphan:
        return []

    created: List[Project] = []
    project = _project_from_path(todo.origin_path, created)

    todo.order_index = len(project.todos)
    todo.parent_project = project
    todo.origin_path = ""
    todo.save()

    return created


def _project_from_path(path: str, created: List[Project]) -> Project:
    """
    The project a path names, building whatever part of it is missing
    """

    names = [name.strip() for name in path.split(PATH_SEPARATOR) if name.strip()]
    parent = Project._get_or_create_root()

    for name in names or [UNKNOWN_PROJECT]:
        child = _child_named(parent, name)

        if child is None:
            child = Project(
                parent_project=parent,
                order_index=len(parent.projects),
            )
            child.description = f"{REVIVED_PREFIX}{name}"
            child.save()
            created.append(child)

        parent = child

    return parent


def _child_named(parent: Project, name: str) -> Optional[Project]:
    """
    The project of this name filed under `parent`, revived or not

    A project that was already brought back once answers to the name it was
    brought back under as well as to its own, so that a second todo out of the
    same dead project joins the first instead of building it all over again.
    """

    for child in parent.projects:
        if child.description in (name, f"{REVIVED_PREFIX}{name}"):
            return child

    return None


def move_project_to_bin(project: Project) -> None:
    """
    Throws a project away, keeping everything that was filed in it

    The project row is the only thing that actually goes. Every todo under it
    — its own, and those of the projects nested inside it — is stamped with
    the path it was filed under and moved to the Bin, so that the work can be
    looked over, restored one row at a time, or dropped for good later on.
    """

    stamp = datetime.now()

    for node in [project, *_sub_projects(project)]:
        path = project_path(node)

        for todo in list(node.todos):
            todo.origin_path = path
            todo.parent_project = None

            for member in _family(todo):
                member.binned_at = stamp

            manager.session.add(todo)

    manager.commit()
    project.drop()


def empty_bin() -> List[str]:
    """
    Deletes everything in the Bin for good, and says which rows those were

    A task goes out the way it went in: whole, with its steps. What comes back
    is every row that was deleted, steps included, so that the panes which
    drew any of them can let go of what they were holding — a row still held
    on to here is one that gets read back out of the database after it has
    left it.
    """

    tasks = binned_tasks()
    gone = [node.uuid for todo in tasks for node in _family(todo)]

    # Only the tasks are handed over: the steps under them go with them, the
    # same way deleting a single task takes its own
    for todo in tasks:
        manager.session.delete(todo)

    manager.commit()

    return gone
