from tests.test_ui.ui_base import run_pilot, create_and_move_to_todo
from dooit.ui.tui import Dooit
from dooit.ui.widgets.trees.todos_tree import TodosTree


async def test_search():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        tree = await create_and_move_to_todo(pilot)

        async def create_todo(tree: TodosTree, description: str):
            tree.add_sibling()
            await pilot.press(*list(description))
            await pilot.press("escape")

        items = ["apple", "apps", "applet", "apricot"]
        for item in items:
            await create_todo(tree, item)

        assert len(tree._options) == 4

        tree.start_search()
        await pilot.pause()

        assert app.bar_switcher.search_bar

        await pilot.press("a")
        assert sum(i.disabled for i in tree._options) == 0

        await pilot.press("p", "p")
        assert sum(i.disabled for i in tree._options) == 1

        await pilot.press("l")
        assert sum(i.disabled for i in tree._options) == 2

        await pilot.press(*(["backspace"] * 4))
        assert sum(i.disabled for i in tree._options) == 0

        await pilot.press(*list("applet"))
        assert sum(i.disabled for i in tree._options) == 3

        # confirm search
        await pilot.press("enter")
        assert app.bar_switcher.current == "status_bar"

        await pilot.press("escape")
        await pilot.pause()
        assert sum(i.disabled for i in tree._options) == 0

        # cancel search
        tree.start_search()
        await pilot.pause()

        await pilot.press("escape")
        assert app.bar_switcher.current == "status_bar"

        await pilot.pause()
        assert sum(i.disabled for i in tree._options) == 0


async def add_todos(pilot, tree: TodosTree, *descriptions: str):
    for description in descriptions:
        tree.add_sibling()
        await pilot.press(*list(description), "escape")


def current(tree: TodosTree) -> str:
    return tree.current_model.description


async def test_search_jumps_to_first_match_and_n_cycles():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        tree = await create_and_move_to_todo(pilot)
        await add_todos(pilot, tree, "apple", "banana", "cherry", "banana split")
        assert current(tree) == "banana split"

        await pilot.press("/", *list("ban"))
        assert current(tree) == "banana"

        await pilot.press("enter")
        assert app.bar_switcher.current == "status_bar"
        assert not any(option.disabled for option in tree._options)
        assert current(tree) == "banana"

        await pilot.press("n")
        assert current(tree) == "banana split"
        await pilot.press("n")
        assert current(tree) == "banana"  # wraps around
        await pilot.press("N")
        assert current(tree) == "banana split"  # wraps backwards


async def test_search_reveals_matches_in_collapsed_items():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        tree = await create_and_move_to_todo(pilot)
        await add_todos(pilot, tree, "fruit")
        tree.add_child_node()
        await pilot.press(*list("kiwi"), "escape")
        tree.highlighted = 0
        await add_todos(pilot, tree, "veg")

        tree.highlighted = 0
        await pilot.press("z")  # collapse fruit
        assert len(tree._options) == 2

        await pilot.press("/", *list("kiwi"), "enter")
        assert current(tree) == "kiwi"

        await pilot.press("Z")  # collapse the parent, cursor on fruit
        assert len(tree._options) == 2

        await pilot.press("n")
        assert current(tree) == "kiwi"
        assert len(tree._options) == 3


async def test_n_without_search():
    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        tree = await create_and_move_to_todo(pilot)
        await add_todos(pilot, tree, "apple")

        await pilot.press("n")
        await pilot.pause()
        assert getattr(app.bar_switcher.visible_content, "message", None) == (
            "No previous search"
        )
