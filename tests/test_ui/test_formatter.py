from typing import Optional
from rich.text import Text
from rich.style import Style
from dooit.api.project import Project
from dooit.ui.api.api_components.formatters import FormatterStore
from dooit.ui.api.dooit_api import DooitAPI
from dooit.ui.api import extra_formatter
from tests.test_ui.ui_base import run_pilot
from dooit.ui.tui import Dooit


def set_italic(value: str, _: Project, api: DooitAPI) -> Optional[str]:
    text_value = Text(value)
    text_value.highlight_words(
        ["test"],
        Style(
            italic=True,
            color=api.vars.theme.red,
        ),
    )
    return text_value.markup


@extra_formatter
def add_icon(value: str, _: Project) -> Optional[str]:
    if "123" in value:
        return f"(icon) {value}"


def add_icon_skip_multiple(value: str, _: Project) -> Optional[str]:
    if "123" in value:
        return f"(icon) {value}"


def setup(api: DooitAPI):
    store = FormatterStore(lambda: None, api)
    p1 = Project(description="this is a test description")
    p2 = Project(description="another description 123")
    return store, p1, p2


def italic_test(api: DooitAPI) -> str:
    """The word "test" as `set_italic` marks it, in the theme's own red

    Rich normalizes hex colors to lowercase on the way through a Style, so
    the expectation has to be lowercased too.
    """

    red = api.vars.theme.red.lower()
    return f"[italic {red}]test[/italic {red}]"


async def test_no_formatting():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        store, p1, p2 = setup(app.api)

        formatted = store.format_value(p1.description, p1)
        assert formatted.markup == "this is a test description"

        formatted = store.format_value(p2.description, p2)
        assert formatted.markup == "another description 123"


async def test_basic_formatting():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        store, p1, p2 = setup(app.api)

        store.add(set_italic)
        formatted = store.format_value(p1.description, p1)
        assert formatted.markup == f"this is a {italic_test(app.api)} description"

        formatted = store.format_value(p2.description, p2)
        assert formatted.markup == "another description 123"


async def test_multiple_formatting():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        store, p1, p2 = setup(app.api)

        store.add(set_italic)
        store.add(add_icon)
        formatted = store.format_value(p1.description, p1)
        assert formatted.markup == f"this is a {italic_test(app.api)} description"

        formatted = store.format_value(p2.description, p2)
        assert formatted.markup == "(icon) another description 123"


async def test_multiple_formatting_skip():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        store, p1, p2 = setup(app.api)
        p2.description = "another description 123 test"

        store.add(set_italic)
        store.add(add_icon_skip_multiple)
        formatted = store.format_value(p1.description, p1)
        assert formatted.markup == f"this is a {italic_test(app.api)} description"

        formatted = store.format_value(p2.description, p2)
        assert formatted.markup == "(icon) another description 123 test"


async def test_multiple_formatting_toggle():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        store, p1, _ = setup(app.api)

        p1.description += " 123"

        store.add(set_italic, id="italic")
        store.add(add_icon, id="icon")
        formatted = store.format_value(p1.description, p1)
        assert (
            formatted.markup
            == f"(icon) this is a {italic_test(app.api)} description 123"
        )

        assert store.disable("italic")
        formatted = store.format_value(p1.description, p1)
        assert formatted.markup == "(icon) this is a test description 123"

        assert store.disable("icon")
        formatted = store.format_value(p1.description, p1)
        assert formatted.markup == "this is a test description 123"

        assert store.enable("italic")
        formatted = store.format_value(p1.description, p1)
        assert formatted.markup == f"this is a {italic_test(app.api)} description 123"

        assert not store.enable("random_gibberish_id")
        assert not store.disable("random_gibberish_id")

        store.remove("italic")
        formatted = store.format_value(p1.description, p1)
        assert formatted.markup == "this is a test description 123"
