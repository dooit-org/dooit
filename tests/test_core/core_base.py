import pytest

from dooit.models import Todo, Workspace, manager

TEMP_PATH = ":memory:"


@pytest.fixture()
def session():
    manager.connect(TEMP_PATH)
    yield manager.session
    manager.session.rollback()
    manager.session.close()


@pytest.fixture(autouse=True)
def setup_teardown(session):
    yield
    session.rollback()
    session.close()


@pytest.fixture
def create_workspace():
    def _inner(desc=None, parent_workspace=None):
        w = Workspace(description=desc, parent_workspace=parent_workspace)
        w.save()
        return w

    return _inner


@pytest.fixture
def create_todo(create_workspace):
    def _inner(desc=None, parent_workspace=None, parent_todo=None):
        if not parent_todo:
            parent_workspace = parent_workspace or create_workspace()

        t = Todo(
            description=desc, parent_workspace=parent_workspace, parent_todo=parent_todo
        )
        t.save()
        return t

    return _inner


@pytest.fixture
def workspace1(create_workspace, create_todo):
    w = create_workspace("workspace 1")

    for desc in ["workspace a", "workspace b", "workspace c"]:
        create_workspace(desc, parent_workspace=w)

    for desc in ["todo a", "todo b", "todo c"]:
        create_todo(desc, parent_workspace=w)

    w.save()
    return w


@pytest.fixture
def todo1(workspace1, create_todo):
    t = create_todo("todo 1", parent_workspace=workspace1)

    for desc in ["todo a", "todo b", "todo c"]:
        create_todo(desc, parent_todo=t)

    return t
