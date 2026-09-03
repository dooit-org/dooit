from .todos_tree import TodosTree
from .fixed_todos_tree import FixedTodosTree
from .projects_tree import ProjectsTree


def make_todos_tree(project) -> TodosTree:
    """
    The tasks pane a project is shown in

    A fixed project gathers its todos from all over the tree and wants them
    grouped; a stored one simply shows what is filed under it.
    """

    if getattr(project, "is_fixed", False):
        return FixedTodosTree(project)

    return TodosTree(project)


__all__ = ["TodosTree", "FixedTodosTree", "ProjectsTree", "make_todos_tree"]
