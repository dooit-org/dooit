from dooit.api.project import Project
from tests.test_core.core_base import *  # noqa


def test_creation_and_deletion(create_project):
    p = create_project()
    assert len(Project.all()) == 1

    p.drop()
    assert len(Project.all()) == 0


def test_shifts_normal(create_project):
    project = [create_project() for _ in range(5)][0]
    assert project is not None

    siblings = project.siblings
    assert project.is_first_sibling()

    project.shift_down()
    siblings = project.siblings
    assert siblings[1].id == project.id

    project.shift_up()
    siblings = project.siblings
    assert siblings[0].id == project.id
    assert project.is_first_sibling()


def test_shifts_edge(create_project):
    projects = [create_project() for _ in range(5)]

    assert not projects[0].shift_up()
    assert not projects[-1].shift_down()


def test_sort_field(create_project):
    names = ["a", "b", "c", "d", "e"][::-1]
    p = [create_project(name) for name in names][0]

    p.sort_siblings("description")
    assert [i.description for i in p.siblings] == sorted(names)


def test_sort_reverse(create_project):
    names = ["a", "b", "c", "d", "e"]
    p = [create_project(name) for name in names][0]

    p.reverse_siblings()
    assert [i.description for i in p.siblings] == names[::-1]
