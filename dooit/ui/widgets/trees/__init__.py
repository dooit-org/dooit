from .todos_tree import TodosTree
from .fixed_todos_tree import FixedTodosTree
from .bin_todos_tree import BinTodosTree
from .completed_todos_tree import CompletedTodosTree
from .projects_tree import ProjectsTree


def make_todos_tree(project) -> TodosTree:
    """
    The tasks pane a project is shown in

    A fixed project gathers its todos from all over the tree and wants them
    grouped; a stored one simply shows what is filed under it. One that gathers
    what has been thrown away needs a pane that draws the binned todos rather
    than hiding them, and one that keeps a row after it has been unticked needs
    a pane that can hold it.
    """

    if not getattr(project, "is_fixed", False):
        return TodosTree(project)

    if getattr(project, "gathers_binned", False):
        return BinTodosTree(project)

    if getattr(project, "holds_unticked_rows", False):
        return CompletedTodosTree(project)

    return FixedTodosTree(project)


__all__ = [
    "TodosTree",
    "FixedTodosTree",
    "BinTodosTree",
    "CompletedTodosTree",
    "ProjectsTree",
    "make_todos_tree",
]
