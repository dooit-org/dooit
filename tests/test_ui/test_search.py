from dooit.ui.widgets.trees.todos_tree import TodosTree
from tests.test_ui.ui_base import run_pilot, create_and_move_to_todo, tree_options
from dooit.ui.tui import Dooit


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

        assert len(tree_options(tree)) == 4

        tree.start_search()
        await pilot.pause()

        assert app.bar_switcher.search_bar

        await pilot.press("a")
        assert sum(i.disabled for i in tree_options(tree)) == 0

        await pilot.press("p", "p")
        assert sum(i.disabled for i in tree_options(tree)) == 1

        await pilot.press("l")
        assert sum(i.disabled for i in tree_options(tree)) == 2

        await pilot.press(*(["backspace"] * 4))
        assert sum(i.disabled for i in tree_options(tree)) == 0

        await pilot.press(*list("applet"))
        assert sum(i.disabled for i in tree_options(tree)) == 3

        # confirm search
        await pilot.press("enter")
        assert app.bar_switcher.current == "status_bar"

        await pilot.press("escape")
        await pilot.pause()
        assert sum(i.disabled for i in tree_options(tree)) == 0

        # cancel search
        tree.start_search()
        await pilot.pause()

        await pilot.press("escape")
        assert app.bar_switcher.current == "status_bar"

        await pilot.pause()
        assert sum(i.disabled for i in tree_options(tree)) == 0
