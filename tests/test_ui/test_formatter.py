from typing import Optional

from dooit.models.workspace import Workspace
from dooit.ui.bridge.components.formatters import FormatterStore
from dooit.ui.tui import Dooit
from tests.test_ui.ui_base import run_pilot


def format_with_prefix(workspace: Workspace) -> Optional[str]:
    return f">> {workspace.description}"


def format_conditional(workspace: Workspace) -> Optional[str]:
    if "123" in workspace.description:
        return f"(icon) {workspace.description}"


def setup(api):
    store = FormatterStore(api)
    w1 = Workspace(description="this is a test description")
    w2 = Workspace(description="another description 123")
    return store, w1, w2


async def test_no_formatting():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        store, w1, w2 = setup(app.api)

        formatted = store.format_value(w1.description, w1)
        assert formatted.markup == "this is a test description"

        formatted = store.format_value(w2.description, w2)
        assert formatted.markup == "another description 123"


async def test_basic_formatting():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        store, w1, w2 = setup(app.api)

        store.set(format_with_prefix)
        formatted = store.format_value(w1.description, w1)
        assert formatted.markup == ">> this is a test description"

        formatted = store.format_value(w2.description, w2)
        assert formatted.markup == ">> another description 123"


async def test_formatting_replaces():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        store, w1, _ = setup(app.api)

        store.set(format_conditional)
        # format_conditional returns None for w1 (no "123"), falls back to str(value)
        formatted = store.format_value(w1.description, w1)
        assert formatted.markup == "this is a test description"

        # adding a new formatter replaces the old one
        store.set(format_with_prefix)
        formatted = store.format_value(w1.description, w1)
        assert formatted.markup == ">> this is a test description"
