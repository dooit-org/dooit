"""
The finder: every task in the database, narrowed down as it is typed

The old search filtered the pane that happened to be in front -- it could only
find what was already on screen, and finding it left the pane greyed out until
escape was pressed. What a search is actually for here is the other thing: a
task is somewhere in the tree, and the point is to get to it.

So this looks through every task there is, whichever project it is filed under
and whether or not it is still to be done, and what it hands back is the one
that was picked. Where the app then goes is `MainScreen.reveal_todo`'s
business.
"""

from datetime import datetime
from itertools import groupby
from typing import Iterable, List, NamedTuple, Optional, Sequence, Tuple

from rich.cells import cell_len
from rich.console import Group, RenderableType
from rich.style import Style
from rich.table import Table
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static

from dooit.api import BIN, COMPLETED, Todo
from dooit.api.fixed_projects import owning_project, project_path
from dooit.api.theme import DooitThemeBase
from dooit.ui.widgets.inputs._input import Input
from dooit.ui.widgets.trees.model_tree import GroupHeading
from dooit.utils import blend, day_label

from .base import BaseScreen

# What the panel is titled, in the border, the way quick add is
PANEL_TITLE = "Find task"

# The glyph the query is typed after, the same one the one line entry uses:
# both are a line typed over the app rather than a field in it
PROMPT = "❯ "

# The folder the projects pane draws its rows with, so the project a task was
# found in is recognisably the row over there
PROJECT_ICON = "󰉋"

# The checkbox the tasks pane draws its rows with, empty and ticked
CHECKBOX_EMPTY = "󰄱"
CHECKBOX_TICKED = "󰄵"

# The calendar a deadline is marked with in the date columns
DATE_ICON = "󰃰"

# How many matches are on screen at once. The rest are still there: the cursor
# scrolls the window over them, and the border says where in the list it is
MAX_ROWS = 10

# How far the things around a match are pulled towards the background: the
# project it is in, and the line that stands in for the results while there
# are none
FADE = 0.45

# How far a task that is no longer being worked on is pulled towards it. Far
# enough that the block reads as gray at a glance, and not so far that it
# cannot be read at all -- the same thing the projects pane does to the two
# rows these come from
MUTED_FADE = 0.55

# What the counter in the bottom border says: where the cursor is in the whole
# list of matches, which is the only place the ones off screen are counted
POSITION = "{} of {}"

HINT = "↑↓  move      enter  go to task      esc  cancel"

# What stands where the results go while there is nothing to put there
EMPTY_QUERY = "Type to find a task"
NO_MATCHES = "No task matches"

# The blocks the matches are drawn in, in the order they are drawn. What is
# still to be done comes first and unheaded, since that is what the finder is
# opened for; the other two are what became of a task, and each is headed by
# the name of the pane it moved to
LIVE, DONE, BINNED = 0, 1, 2

SECTION_LABELS = {DONE: COMPLETED.title, BINNED: BIN.title}


def task_root(todo: Todo) -> Todo:
    """
    The task a todo belongs to: itself, unless it is a step of another one
    """

    node = todo

    while node.parent_todo is not None:
        node = node.parent_todo

    return node


def section_of(todo: Todo) -> int:
    """
    Which block a task is drawn in, which is also where it is to be found

    A task follows its family: a step is wherever the task it belongs to went,
    since that is the pane it is drawn in. A finished step of a task still
    being worked on has gone nowhere, and stays among the live rows.
    """

    if todo.is_binned:
        return BINNED

    if not task_root(todo).pending:
        return DONE

    return LIVE


class Candidate(NamedTuple):
    """
    A task, with everything the query is matched against worked out once

    The list is built when the finder opens and read on every keystroke, so
    the project paths are walked once rather than once per letter.
    """

    todo: Todo
    project: str
    haystack: str
    section: int


class Match(NamedTuple):
    candidate: Candidate
    # What the matches are ordered by; see `rank` below
    order: tuple


def candidates() -> List[Candidate]:
    result = []

    for todo in Todo.all():
        project = owning_project(todo)
        path = project_path(project) if project else ""
        result.append(
            Candidate(
                todo=todo,
                project=path,
                haystack=f"{todo.description}\n{path}".lower(),
                section=section_of(todo),
            )
        )

    return result


def _due_key(todo: Todo) -> tuple:
    """
    Sorts the dated tasks by their deadline, and the undated ones after them
    """

    if todo.due is None:
        return (1, datetime.max)

    return (0, todo.due)


def rank(candidate: Candidate, terms: Sequence[str]) -> Optional[tuple]:
    """
    How well a task answers the query, or None when it does not answer it

    Every word typed has to turn up somewhere -- in the description or in the
    project path -- which is what lets a task be found by where it is as well
    as by what it says ("api tests"). The work still to do comes first
    whatever it says, since a finished task is usually being looked up rather
    than looked for.

    Within a block what decides the order is the first word alone: a
    description that starts with it, then one with a word starting with it,
    then one that merely contains it, then the tasks that only matched on
    their project. And within a rank the nearest deadline leads, since two
    tasks that read alike are told apart by when they are wanted.
    """

    if not all(term in candidate.haystack for term in terms):
        return None

    description = candidate.todo.description.lower()
    lead = terms[0]

    if description.startswith(lead):
        position = 0
    elif any(word.startswith(lead) for word in description.split()):
        position = 1
    elif lead in description:
        position = 2
    else:
        position = 3

    return (candidate.section, position, _due_key(candidate.todo), description)


def search(pool: Sequence[Candidate], query: str) -> List[Candidate]:
    """
    The tasks that answer the query, best first
    """

    terms = query.lower().split()

    if not terms:
        return []

    matches = []

    for candidate in pool:
        order = rank(candidate, terms)

        if order is not None:
            matches.append(Match(candidate, order))

    matches.sort(key=lambda match: match.order)
    return [match.candidate for match in matches]


class SearchScreen(BaseScreen, ModalScreen):
    """
    The panel the query is typed into, over a dimmed copy of the app

    An overlay rather than a bar, for the same reason quick add is one: what
    is being typed is a question, and the answer to it is a list that has to
    go somewhere. The app stays visible behind it, since where the picked task
    is about to be found is over there.
    """

    def __init__(self) -> None:
        super().__init__()

        self._input = Input()
        self._input.is_editing = True

        self._pool: List[Candidate] = []
        self._matches: List[Candidate] = []

        # Which of the matches the cursor is on, counted through the whole
        # list rather than through what is on screen. Always the first one
        # after a keystroke: the list is reordered under it, so wherever the
        # cursor had got to means nothing once the query has changed
        self._index = 0

        # The match the window starts at, which is what the cursor pushes
        # along when it walks past either end of it
        self._offset = 0

    @property
    def theme(self) -> DooitThemeBase:
        return self.api.vars.theme

    @property
    def panel(self) -> Static:
        return self.query_one("#search-panel", Static)

    @property
    def hint(self) -> Static:
        return self.query_one("#search-hint", Static)

    def compose(self) -> ComposeResult:
        yield Static(id="search-panel")
        yield Static(HINT, id="search-hint")

    def on_mount(self) -> None:
        self.panel.border_title = PANEL_TITLE
        self._pool = candidates()
        self._redraw()

    # ------------------------------------------------------------------
    # Typing
    # ------------------------------------------------------------------

    async def handle_key(self, event: events.Key) -> bool:
        # Every key belongs to the query, including the ones the app binds
        # elsewhere: this is a text field, and `q` is a letter in it
        event.stop()

        key = self.resolve_key(event)

        if key == "escape":
            self.dismiss(None)
            return True

        if key == "enter":
            self.dismiss(self.selected)
            return True

        # The list is walked with the arrows, and with the keys a terminal
        # walks a list with while the hands are still on the letters
        if key in ("down", "ctrl+n"):
            self._move(1)
            return True

        if key in ("up", "ctrl+p"):
            self._move(-1)
            return True

        self._input.keypress(key)
        self._research()

        return True

    @property
    def selected(self) -> Optional[Todo]:
        if not self._matches:
            return None

        return self._matches[self._index].todo

    def _move(self, step: int) -> None:
        """
        Moves the cursor through every match, and the window along with it

        The list is walked round rather than stopped at either end: what is
        wanted is usually near the top, and a cursor sent up from there gets
        to the bottom of the list in one key.
        """

        if not self._matches:
            return

        self._index = (self._index + step) % len(self._matches)

        if self._index < self._offset:
            self._offset = self._index
        elif self._index >= self._offset + MAX_ROWS:
            self._offset = self._index - MAX_ROWS + 1

        self._redraw()

    def _research(self) -> None:
        self._matches = search(self._pool, self._input.value)
        self._index = 0
        self._offset = 0
        self._redraw()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _redraw(self) -> None:
        self.panel.update(Group(self._line(), Text(), self._results()))

        # Where the cursor is in a list that mostly does not fit: without it a
        # window scrolled halfway down says nothing about how much is left
        self.panel.border_subtitle = (
            POSITION.format(self._index + 1, len(self._matches))
            if self._matches
            else ""
        )

    def _line(self) -> Text:
        # The buffer draws itself rather than being handed over as a string,
        # so that a selection made in it is highlighted here too
        buffer = self._input.render_editing(self.theme)
        buffer.style = Style(color=self.theme.foreground3)

        return Text(PROMPT, style=Style(color=self.theme.primary, bold=True)) + buffer

    def _faded(self, message: str) -> Text:
        return Text(
            message,
            style=Style(
                color=blend(self.theme.foreground1, self.theme.background2, FADE)
            ),
        )

    def _results(self) -> RenderableType:
        if not self._input.value.strip():
            return self._faded(EMPTY_QUERY)

        if not self._matches:
            return self._faded(NO_MATCHES)

        terms = self._input.value.lower().split()
        window = list(
            enumerate(
                self._matches[self._offset : self._offset + MAX_ROWS],
                start=self._offset,
            )
        )
        widths = self._column_widths(candidate for _, candidate in window)

        blocks: List[RenderableType] = []

        # Grouped rather than sliced by section: a window scrolled into the
        # middle of the list can hold the end of one block and the start of
        # the next, and each still has to be drawn under its own name
        for section, rows in groupby(window, key=lambda row: row[1].section):
            if section != LIVE:
                blocks.append(self._heading(section, space_above=bool(blocks)))

            blocks.append(self._table(list(rows), terms, widths))

        return Group(*blocks)

    def _heading(self, section: int, space_above: bool) -> GroupHeading:
        """
        The name of a block, with a hairline running out to the panel edge

        The same heading the tasks pane divides its blocks with, so a run of
        rows under a name reads the same here as it does over there.
        """

        theme = self.theme

        return GroupHeading(
            label=SECTION_LABELS[section],
            label_style=blend(theme.foreground1, theme.background2, FADE),
            rule_style=theme.background3,
            space_above=space_above,
        )

    def _column_widths(self, window: Iterable[Candidate]) -> Tuple[int, int]:
        """
        How wide the deadline and the project are drawn, across every block

        Fixed here rather than left to each block's own table, or the columns
        would step sideways at every heading: what a block holds says nothing
        about where the columns of the panel are.
        """

        due = 0
        project = 0

        for candidate in window:
            due = max(due, cell_len(self._due(candidate.todo).plain))
            project = max(project, cell_len(self._project(candidate).plain))

        return due, project

    def _table(
        self,
        rows: List[Tuple[int, Candidate]],
        terms: Sequence[str],
        widths: Tuple[int, int],
    ) -> Table:
        # Filled to the width of the panel rather than to the longest row, so
        # that the project a task is in lines up down the right hand side and
        # the cursor is a band rather than a ragged patch
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(width=1)
        table.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
        table.add_column(justify="right", no_wrap=True, width=widths[0])
        table.add_column(justify="right", no_wrap=True, width=widths[1])

        for index, candidate in rows:
            table.add_row(
                self._status(candidate),
                self._description(candidate, terms),
                self._due(candidate.todo),
                self._project(candidate),
                style=self._row_style(index),
            )

        return table

    def _row_style(self, index: int) -> Style:
        if index != self._index:
            return Style()

        return Style(bgcolor=self.theme.background3)

    def _muted(self, color: str) -> str:
        """A color as a task nobody is working on any more wears it"""

        return blend(color, self.theme.background2, MUTED_FADE)

    def _status(self, candidate: Candidate) -> Text:
        """
        The checkbox the row wears in the pane, in the color its priority
        gives it there -- and gray, like everything else on the row, once the
        task is done with
        """

        theme = self.theme
        todo = candidate.todo
        colors = {1: theme.red, 2: theme.yellow, 3: theme.cyan}
        color = colors.get(
            todo.priority, blend(theme.foreground1, theme.background2, 0.5)
        )

        if candidate.section != LIVE:
            color = self._muted(theme.foreground1)
        elif todo.is_completed:
            color = blend(color, theme.background2, 0.35)

        return Text(
            CHECKBOX_TICKED if todo.is_completed else CHECKBOX_EMPTY,
            style=Style(color=color, bold=True),
        )

    def _description(self, candidate: Candidate, terms: Sequence[str]) -> Text:
        """
        What the task says, with what was typed picked out of it

        The words are marked wherever they landed rather than only at the
        front, which is what shows why a row is in the list at all when the
        match is halfway down a long description.
        """

        theme = self.theme
        live = candidate.section == LIVE
        color = theme.foreground2 if live else self._muted(theme.foreground1)
        accent = theme.primary if live else self._muted(theme.primary)

        description = candidate.todo.description
        text = Text(description, style=Style(color=color))
        lower = description.lower()
        style = Style(color=accent, bold=True)

        for term in terms:
            start = lower.find(term)

            while start != -1:
                text.stylize(style, start, start + len(term))
                start = lower.find(term, start + len(term))

        return text

    def _due(self, todo: Todo) -> Text:
        """
        The deadline, if the task has one: overdue in red and still ahead in
        yellow, the way the date columns are colored. A task that is over with
        is late for nothing, so its date is drawn gray with the rest of it.
        """

        if todo.due is None:
            return Text()

        if section_of(todo) != LIVE:
            color = self._muted(self.theme.foreground1)
        else:
            color = self.theme.red if todo.is_overdue else self.theme.yellow

        return Text(f"{DATE_ICON} {day_label(todo.due)}", style=Style(color=color))

    def _project(self, candidate: Candidate) -> Text:
        if not candidate.project:
            return Text()

        theme = self.theme

        if candidate.section == LIVE:
            color = blend(theme.primary, theme.background2, FADE)
        else:
            color = self._muted(theme.foreground1)

        return Text(f"{PROJECT_ICON} {candidate.project}", style=Style(color=color))
