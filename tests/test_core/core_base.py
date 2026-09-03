from dooit.api import manager
from dooit.api import Project, Todo
import pytest

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
def create_project():
    def _inner(desc=None, parent_project=None):
        p = Project(description=desc, parent_project=parent_project)
        p.save()
        return p

    return _inner


@pytest.fixture
def create_todo(create_project):
    def _inner(desc=None, parent_project=None, parent_todo=None):
        if not parent_todo:
            parent_project = parent_project or create_project()

        t = Todo(
            description=desc, parent_project=parent_project, parent_todo=parent_todo
        )
        t.save()
        return t

    return _inner


@pytest.fixture
def project1(create_project, create_todo):
    p = create_project("project 1")

    for desc in ["project a", "project b", "project c"]:
        create_project(desc, parent_project=p)

    for desc in ["todo a", "todo b", "todo c"]:
        create_todo(desc, parent_project=p)

    p.save()
    return p


@pytest.fixture
def todo1(project1, create_todo):
    t = create_todo("todo 1", parent_project=project1)

    for desc in ["todo a", "todo b", "todo c"]:
        create_todo(desc, parent_todo=t)

    return t
