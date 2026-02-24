from dooit.models.workspace import Workspace
from tests.test_core.core_base import *  # noqa


def test_creation_and_deletion(create_workspace):
    w = create_workspace()
    assert len(Workspace.all()) == 1

    w.drop()
    assert len(Workspace.all()) == 0


def test_shifts_normal(create_workspace):
    workspace = [create_workspace() for _ in range(5)][0]
    assert workspace is not None

    siblings = workspace.siblings
    assert workspace.is_first_sibling()

    workspace.shift_down()
    siblings = workspace.siblings
    assert siblings[1].id == workspace.id

    workspace.shift_up()
    siblings = workspace.siblings
    assert siblings[0].id == workspace.id
    assert workspace.is_first_sibling()


def test_shifts_edge(create_workspace):
    workspaces = [create_workspace() for _ in range(5)]

    assert not workspaces[0].shift_up()
    assert not workspaces[-1].shift_down()


def test_sort_field(create_workspace):
    names = ["a", "b", "c", "d", "e"][::-1]
    w = [create_workspace(name) for name in names][0]

    w.sort_siblings("description")
    assert [i.description for i in w.siblings] == sorted(names)


def test_sort_reverse(create_workspace):
    names = ["a", "b", "c", "d", "e"]
    w = [create_workspace(name) for name in names][0]

    w.reverse_siblings()
    assert [i.description for i in w.siblings] == names[::-1]
