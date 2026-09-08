"""
The projects pane: stored projects among the fixed ones
"""

from dooit.api import BIN, TODAY, Project, Todo
from tests.test_ui.ui_base import (
    boot,
    commit_line,
    highlighted_index,
    new_project,
    notification_message,
    run_pilot,
    set_clipboard,
    tree_options,
    visible_todos,
)


async def test_projects_tree_basics():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        assert len(tree_options(ptree)) == 0

        # Direct model additions draw a row each
        ptree.add_project()
        ptree.add_project()
        ptree.add_project()
        p = ptree.add_project()

        assert len(tree_options(ptree)) == 4

        # Highlighting a project brings its pane to the front
        ptree.highlight_id(p)
        await pilot.pause()

        assert highlighted_index(ptree) == 3
        assert visible_todos(app).model.uuid == p

        # Child nodes hide and show with their parent's expansion
        child = ptree.current_model.add_project()
        child.description = "child"
        child.save()
        ptree.force_refresh()

        assert len(tree_options(ptree)) == 4  # collapsed

        ptree.toggle_expand()
        assert len(tree_options(ptree)) == 5

        ptree.toggle_expand()
        assert len(tree_options(ptree)) == 4


async def test_add_and_commit_with_enter():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        await pilot.press("j", "n")
        await commit_line(pilot, "first")

        assert [p.description for p in Project.all()] == ["first"]
        assert highlighted_index(ptree) == 0

        await pilot.press("n")
        await commit_line(pilot, "second")

        assert len(tree_options(ptree)) == 2
        assert highlighted_index(ptree) == 1


async def test_escape_discards_a_new_project():
    """A project left without a name is nothing to keep"""

    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        await pilot.press("j", "n")
        await pilot.press(*list("never kept"))
        await pilot.press("escape")
        await pilot.pause()

        assert Project.all() == []
        assert tree_options(ptree) == []


async def test_blank_name_is_dropped_even_on_enter():
    async with run_pilot() as pilot:
        await boot(pilot)

        await pilot.press("j", "n")
        await commit_line(pilot, "   ")

        assert Project.all() == []


async def test_renaming_a_project():
    async with run_pilot() as pilot:
        await boot(pilot)
        await new_project(pilot, "old name")

        await pilot.press("i")
        # A fresh edit starts with the old name in the buffer; wipe it
        await pilot.press("ctrl+l")
        await commit_line(pilot, "new name")

        assert [p.description for p in Project.all()] == ["new name"]


async def test_nested_project_via_child_key():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        outer = await new_project(pilot, "outer")

        await pilot.press("N")
        await commit_line(pilot, "inner")

        inner = next(p for p in Project.all() if p.description == "inner")
        assert inner.parent_project == outer

        # The parent was expanded to show it, and the cursor is on it
        assert len(tree_options(ptree)) == 2
        assert ptree.current_model.uuid == inner.uuid

        # `h` folds the parent away again
        await pilot.press("k")  # up to the parent
        await pilot.press("h")
        await pilot.pause()

        assert len(tree_options(ptree)) == 1


async def test_empty_bin_from_anywhere_notifies_when_empty():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await pilot.press("Y", "Y")
        await pilot.pause()

        assert notification_message(app) == "The Bin is already empty"


async def test_fixed_projects_cannot_be_edited():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        # The keys act on the focused pane, so the projects pane first;
        # its cursor starts on Today, a fixed project
        await pilot.press("j")
        assert ptree.current_model is TODAY

        for key in ("i",):
            await pilot.press(key)
            await pilot.pause()
            assert not ptree.is_editing

        message = notification_message(app)
        assert message is not None and "fixed project" in message

        # Deleting is refused the same way, without a confirm
        await pilot.press("y", "y")
        await pilot.pause()
        assert app.bar_switcher.current != "confirm_bar"

        # Shifting is refused too
        await pilot.press("K")
        await pilot.press("L")
        await pilot.pause()
        assert ptree.current_model is TODAY


async def test_adding_from_a_fixed_row_starts_the_stored_block():
    """`n` on Today has no sibling to add beside; it starts the tree"""

    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        assert ptree.current_model is TODAY

        await pilot.press("j", "n")
        await commit_line(pilot, "first real project")

        project = Project.all()[0]
        assert project.description == "first real project"
        assert project.parent_project is not None
        assert project.parent_project.is_root


async def test_project_remove_cancelled():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        await new_project(pilot, "keep me")
        p1 = ptree.current_model

        await pilot.press("y", "y")
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()

        assert [p.description for p in Project.all()] == ["keep me"]
        assert visible_todos(app).model.uuid == p1.uuid


async def test_project_delete_for_good():
    async with run_pilot() as pilot:
        await boot(pilot)

        await new_project(pilot, "doomed")

        await pilot.press("y", "y")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()

        assert Project.all() == []


async def test_project_to_bin_keeps_its_work():
    """`xx` on a project throws only the row away; the work lands in the Bin"""

    async with run_pilot() as pilot:
        await boot(pilot)

        await new_project(pilot, "dropped")
        await pilot.press("ö", "n")
        await commit_line(pilot, "orphaned work")

        await pilot.press("j")
        await pilot.press("x", "x")
        await pilot.pause()

        assert Project.all() == []

        todo = Todo.all()[0]
        assert todo.is_binned
        assert todo.origin_path == "dropped"
        assert BIN.todos == [todo]


async def test_shifts():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        await new_project(pilot, "one")
        await pilot.press("n")
        await commit_line(pilot, "two")

        assert highlighted_index(ptree) == 1

        # Shift the highlighted project up, then against the edges.
        # `Project.all()` comes back in insertion order, so the filing has to
        # be read off order_index the way the pane reads it.
        await pilot.press("K")
        await pilot.pause()
        assert highlighted_index(ptree) == 0
        filed = sorted(Project.all(), key=lambda p: p.order_index)
        assert [p.description for p in filed] == ["two", "one"]

        await pilot.press("K")
        await pilot.pause()
        assert highlighted_index(ptree) == 0

        await pilot.press("L")
        await pilot.pause()
        assert highlighted_index(ptree) == 1

        await pilot.press("L")
        await pilot.pause()
        assert highlighted_index(ptree) == 1


async def test_cursor_movement_spans_fixed_and_stored_rows():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        await new_project(pilot, "only")
        assert highlighted_index(ptree) == 0

        # Up from the first stored project climbs into the fixed block
        await pilot.press("k")
        assert ptree.current_model.uuid == "FixedProject_upcoming"

        await pilot.press("k")
        assert ptree.current_model is TODAY

        # And the top of the pane is the top
        await pilot.press("k")
        assert ptree.current_model is TODAY

        # Down walks back over the project and into the pinned block
        await pilot.press("l", "l")
        assert highlighted_index(ptree) == 0

        await pilot.press("l")
        assert ptree.current_model.uuid == "FixedProject_completed"


async def test_go_to_top_and_bottom_stay_on_stored_projects():
    """`gg` and `G` move between the projects, not the panes' furniture"""

    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        await new_project(pilot, "one")
        await pilot.press("n")
        await commit_line(pilot, "two")
        await pilot.press("n")
        await commit_line(pilot, "three")

        await pilot.press("g", "g")
        await pilot.pause()
        assert highlighted_index(ptree) == 0

        await pilot.press("G")
        await pilot.pause()
        assert highlighted_index(ptree) == 2


async def test_add_sibling_while_editing_is_refused():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        await pilot.press("j", "n")  # editing now
        ptree.add_sibling()  # refused mid-edit

        await commit_line(pilot, "project")

        assert len(tree_options(ptree)) == 1
        assert highlighted_index(ptree) == 0


async def test_paste_as_sibling():
    async with run_pilot() as pilot:
        app = await boot(pilot)
        ptree = app.project_tree

        await pilot.press("j")
        await pilot.pause()

        set_clipboard(" pasted   project \n")

        # The first paste has nothing to sit beside, so it starts the tree
        await pilot.press("ctrl+v")
        await pilot.pause()

        assert len(tree_options(ptree)) == 1

        # A description is one line, whatever the clipboard was
        assert ptree.current_model.description == "pasted project"

        # And it is a description like any other: `i` opens the edit on the
        # pasted text rather than on the empty string the node was made as
        await pilot.press("i")
        await pilot.pause()
        assert ptree.current.description.value == "pasted project"

        await pilot.press("escape")
        await pilot.pause()
        assert ptree.current_model.description == "pasted project"

        await pilot.press("ctrl+v")
        await pilot.pause()

        assert len(tree_options(ptree)) == 2
        assert highlighted_index(ptree) == 1

        # Nothing on the clipboard is nothing to add
        set_clipboard("   ")
        await pilot.press("ctrl+v")
        await pilot.pause()

        assert len(tree_options(ptree)) == 2


async def test_copy_description():
    async with run_pilot() as pilot:
        app = await boot(pilot)

        await new_project(pilot, "nixos")

        await pilot.press("ctrl+c")
        await pilot.pause()

        assert app.clipboard == "nixos"
