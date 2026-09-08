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


def test_total_todos_counts_open_work_at_every_level(create_project):
    """The tally beside a project counts work left, however it is filed"""

    from dooit.api import move_todo_to_bin

    p = create_project("home")
    sub = Project(description="garden", parent_project=p)
    sub.save()

    task = p.add_todo()
    task.add_todo()
    sub.add_todo()

    # The task, its step, and the one in the sub project
    assert p.total_todos == 3
    assert sub.total_todos == 1

    done = p.add_todo()
    done.toggle_complete()
    assert p.total_todos == 3

    binned = p.add_todo()
    move_todo_to_bin(binned)
    assert p.total_todos == 3


def test_total_projects(create_project):
    p = create_project("outer")
    assert p.total_projects == 0

    inner = Project(description="inner", parent_project=p)
    inner.save()
    deepest = Project(description="deepest", parent_project=inner)
    deepest.save()

    assert p.total_projects == 2
    assert inner.total_projects == 1

