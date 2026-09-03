from dooit.api import Project
from tests.test_core.core_base import *  # noqa


def test_project_creation(create_project):
    _ = [create_project() for _ in range(5)]
    assert len(Project.all()) == 5


def test_siblings_by_creation(create_project):
    project = [create_project() for _ in range(5)][0]
    assert len(project.siblings) == 5


def test_sibling_methods(create_project):
    project = [create_project() for _ in range(5)][0]
    siblings = project.siblings
    index_ids = [p.order_index for p in siblings]

    assert siblings[0].is_first_sibling()
    assert siblings[-1].is_last_sibling()
    assert index_ids == [0, 1, 2, 3, 4]


def test_parent_kind(create_project):
    project1 = create_project()
    project2 = create_project(parent_project=project1)

    assert project2.has_same_parent_kind


def test_sibling_add(create_project):
    p1 = create_project()

    p1.add_sibling()
    p2 = p1.add_sibling()

    assert len(p1.siblings) == 3
    assert len(p2.siblings) == 3
    assert p2.order_index == 1


def test_project_add(create_project):
    super_project = create_project()

    super_project.add_project()
    p = super_project.add_project()

    assert len(p.siblings) == 2
    assert p.order_index == 1


def test_todo_add(create_project):
    super_project = create_project()

    super_project.add_todo()
    todo = super_project.add_todo()

    assert len(todo.siblings) == 2
    assert todo.order_index == 1


def test_comparable_fields():
    fields = Project.comparable_fields()
    expected_fields = ["description"]
    assert fields == expected_fields


def test_nest_level(create_project):
    p = create_project()
    assert p.nest_level == 0

    p = p.add_project()
    assert p.nest_level == 1

    p = p.add_project()
    assert p.nest_level == 2


def test_root():
    assert len(Project.all()) == 0


def test_clone_from_id(create_project, create_todo):
    # Create source project with nested structure
    p = create_project("Test Project")
    p.description = "Source Project"
    p.save()

    # Add child projects
    child_project1 = p.add_project()
    child_project1.description = "Child Project 1"
    child_project1.save()

    child_project2 = p.add_project()
    child_project2.description = "Child Project 2"
    child_project2.save()

    # Add a nested project
    nested_project = child_project1.add_project()
    nested_project.description = "Nested Project"
    nested_project.save()

    # Add todos to projects
    todo1 = p.add_todo()
    todo1.description = "Parent Todo"
    todo1.save()

    child_todo = todo1.add_todo()
    child_todo.description = "Child Todo"
    child_todo.save()

    todo2 = child_project1.add_todo()
    todo2.description = "Project Child Todo"
    todo2.save()

    # Clone the project
    cloned_project = Project.clone_from_id(p.id, 0)

    # Check basic properties were copied
    assert cloned_project.id != p.id
    assert cloned_project.description == "Source Project"
    assert cloned_project.order_index == 0
    assert cloned_project.parent_project_id == p.parent_project_id

    # Check child projects were cloned
    assert len(cloned_project.projects) == 2

    # Check project descriptions
    child_descriptions = [child.description for child in cloned_project.projects]
    assert "Child Project 1" in child_descriptions
    assert "Child Project 2" in child_descriptions

    # Find the cloned Child Project 1
    cloned_child_project1 = next(
        child
        for child in cloned_project.projects
        if child.description == "Child Project 1"
    )

    # Check nested project was cloned
    assert len(cloned_child_project1.projects) == 1
    assert cloned_child_project1.projects[0].description == "Nested Project"

    # Check todos were cloned
    assert len(cloned_project.todos) == 1
    assert cloned_project.todos[0].description == "Parent Todo"

    # Check child todo was cloned
    assert len(cloned_project.todos[0].todos) == 1
    assert cloned_project.todos[0].todos[0].description == "Child Todo"

    # Check project child todo was cloned
    assert len(cloned_child_project1.todos) == 1
    assert cloned_child_project1.todos[0].description == "Project Child Todo"
