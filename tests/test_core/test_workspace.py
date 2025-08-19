from dooit.api import Workspace
from tests.test_core.core_base import *  # noqa


def test_workspace_creation(create_workspace):
    _ = [create_workspace() for _ in range(5)]
    assert len(Workspace.all()) == 5


def test_siblings_by_creation(create_workspace):
    workspace = [create_workspace() for _ in range(5)][0]
    assert len(workspace.siblings) == 5


def test_sibling_methods(create_workspace):
    workspace = [create_workspace() for _ in range(5)][0]
    siblings = workspace.siblings
    index_ids = [w.order_index for w in siblings]

    assert siblings[0].is_first_sibling()
    assert siblings[-1].is_last_sibling()
    assert index_ids == [0, 1, 2, 3, 4]


def test_parent_kind(create_workspace):
    workspace1 = create_workspace()
    workspace2 = create_workspace(parent_workspace=workspace1)

    assert workspace2.has_same_parent_kind


def test_sibling_add(create_workspace):
    w1 = create_workspace()

    w1.add_sibling()
    w2 = w1.add_sibling()

    assert len(w1.siblings) == 3
    assert len(w2.siblings) == 3
    assert w2.order_index == 1


def test_workspace_add(create_workspace):
    super_w = create_workspace()

    super_w.add_workspace()
    w = super_w.add_workspace()

    assert len(w.siblings) == 2
    assert w.order_index == 1


def test_todo_add(create_workspace):
    super_w = create_workspace()

    super_w.add_todo()
    todo = super_w.add_todo()

    assert len(todo.siblings) == 2
    assert todo.order_index == 1


def test_comparable_fields():
    fields = Workspace.comparable_fields()
    expected_fields = ["description"]
    assert fields == expected_fields


def test_nest_level(create_workspace):
    w = create_workspace()
    assert w.nest_level == 0

    w = w.add_workspace()
    assert w.nest_level == 1

    w = w.add_workspace()
    assert w.nest_level == 2


def test_root():
    assert len(Workspace.all()) == 0


def test_clone_from_id(create_workspace, create_todo):
    # Create source workspace with nested structure
    w = create_workspace("Test Workspace")
    w.description = "Source Workspace"
    w.save()

    # Add child workspaces
    child_ws1 = w.add_workspace()
    child_ws1.description = "Child Workspace 1"
    child_ws1.save()

    child_ws2 = w.add_workspace()
    child_ws2.description = "Child Workspace 2"
    child_ws2.save()

    # Add a nested workspace
    nested_ws = child_ws1.add_workspace()
    nested_ws.description = "Nested Workspace"
    nested_ws.save()

    # Add todos to workspaces
    todo1 = w.add_todo()
    todo1.description = "Parent Todo"
    todo1.save()

    child_todo = todo1.add_todo()
    child_todo.description = "Child Todo"
    child_todo.save()

    todo2 = child_ws1.add_todo()
    todo2.description = "Workspace Child Todo"
    todo2.save()

    # Clone the workspace
    cloned_workspace = Workspace.clone_from_id(w.id, 0)

    # Check basic properties were copied
    assert cloned_workspace.id != w.id
    assert cloned_workspace.description == "Source Workspace"
    assert cloned_workspace.order_index == 0
    assert cloned_workspace.parent_workspace_id == w.parent_workspace_id

    # Check child workspaces were cloned
    assert len(cloned_workspace.workspaces) == 2

    # Check workspace descriptions
    child_descriptions = [child.description for child in cloned_workspace.workspaces]
    assert "Child Workspace 1" in child_descriptions
    assert "Child Workspace 2" in child_descriptions

    # Find the cloned Child Workspace 1
    cloned_child_ws1 = next(
        child
        for child in cloned_workspace.workspaces
        if child.description == "Child Workspace 1"
    )

    # Check nested workspace was cloned
    assert len(cloned_child_ws1.workspaces) == 1
    assert cloned_child_ws1.workspaces[0].description == "Nested Workspace"

    # Check todos were cloned
    assert len(cloned_workspace.todos) == 1
    assert cloned_workspace.todos[0].description == "Parent Todo"

    # Check child todo was cloned
    assert len(cloned_workspace.todos[0].todos) == 1
    assert cloned_workspace.todos[0].todos[0].description == "Child Todo"

    # Check workspace child todo was cloned
    assert len(cloned_child_ws1.todos) == 1
    assert cloned_child_ws1.todos[0].description == "Workspace Child Todo"
