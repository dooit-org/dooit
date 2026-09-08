from datetime import date, datetime, timedelta
from functools import partial
from typing import Callable, Optional
from rich.style import Style
from dooit.api import Todo, Project
from dooit_extras.formatters import (
    description_highlight_link,
    description_highlight_tags,
    due_danger_today,
    effort_icon,
    recurrence_icon,
)
from dooit_extras.bar_widgets import (
    Clock,
    CurrentProject,
    Powerline,
    Spacer,
    StatusIcons,
    ProjectProgress,
)
from dooit.ui.api import DooitAPI, extra_formatter, subscribe
from dooit.ui.api.dooit_api import SORT_LABELS
from dooit.ui.api.widgets import TodoWidget, ProjectWidget
from dooit.ui.api.events import ModeChanged, Startup
from dooit.ui.screens import HelpScreen
from dooit.ui.widgets.bars import StatusBarWidget
from dooit.ui.widgets.inputs.model_inputs import Recurrence
from dooit.utils import DATE_FORMAT, WEEKDAY_NAMES, blend
from rich.text import Text


# Todo formatters


# The task tally on a project and the child count trailing a todo description
# share one color: the accent the column headers are drawn in, pulled towards the
# background so the numbers annotate the rows they sit on instead of competing
# with them.
COUNT_FADE = 0.4


def count_color(api: DooitAPI) -> str:
    return blend(api.vars.theme.primary, api.vars.theme.background1, COUNT_FADE)


# Priority 1 is the most urgent one; 0 means no priority was set
PRIORITIES = (1, 2, 3)


def priority_color(priority: int, api: DooitAPI) -> str:
    theme = api.vars.theme
    colors = {
        1: theme.red,
        2: theme.yellow,
        # p3 is the calm end of the scale, so it takes the theme's light blue
        # rather than a green that reads as "done" beside the due-date colors
        3: theme.cyan,
    }

    # Nothing prioritized: a gray sitting halfway between text and background
    return colors.get(priority, blend(theme.foreground1, theme.background1, 0.5))


# The orders a project's todos can be read in, in the order the help lists
# them. Priority leads because it is the one a project is opened to ask:
# whatever is filed in here, what is the next thing to do out of it. The dates
# are there for the stretches of work that are run off a calendar instead, and
# hold until they are switched back — the order is the pane's, not a project's.
SORT_MODES = ("priority", "due", "scheduled")


# Effort runs the opposite way to priority: e1 is a quick job, e3 a big one.
# 0 means no estimate was made, and shows as an empty column.
EFFORTS = (1, 2, 3)


# The traffic light everyone reads without being told: cheap is green, costly
# is red. It says the same thing as the due column's colors do, which is what
# lets both be scanned in one pass down the row.
def effort_color(effort: int, api: DooitAPI) -> str:
    theme = api.vars.theme
    colors = {
        1: theme.green,
        2: theme.yellow,
        3: theme.red,
    }

    return colors.get(effort, theme.foreground1)


CHECKBOX_EMPTY = "󰄱"
CHECKBOX_TICKED = "󰄵"


# A rounded checkbox, ticked once the todo is done. It carries the priority
# color, so a row's urgency reads from the very first column and needs no column
# of its own; the tick only pulls that color a notch towards the background,
# dimming it without draining it the way the other columns get grayed out.
def todo_status_formatter(status: str, todo: Todo, api: DooitAPI):
    completed = status == "completed"
    color = priority_color(todo.priority, api)

    if completed:
        color = blend(color, api.vars.theme.background1, 0.35)

    return Text(
        CHECKBOX_TICKED if completed else CHECKBOX_EMPTY,
        style=Style(color=color, bold=True),
    )


# A "week" of lead time means five Austrian working days: Sat and Sun don't
# count (public holidays are ignored).
WORKING_DAYS_PER_WEEK = 5


def _add_working_days(start: date, days: int) -> date:
    current = start

    while days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days -= 1

    return current


# A todo carries two dates: `due`, the deadline it has to be done by, and
# `scheduled`, the day it is planned to be worked on. Both columns are rendered
# by the formatters below, which differ only in the field they read.
#
# German date convention: weekday first, then day, dot separated, and the year
# always spelled out as its last two digits. The time only shows up when it is
# something other than midnight.
def todo_date_formatter(value: Optional[datetime], _: Todo) -> str:
    if value is None:
        return ""

    dt_format = DATE_FORMAT

    if value.hour or value.minute:
        dt_format += " (%H:%M)"

    return f"{WEEKDAY_NAMES[value.weekday()]}, {value.strftime(dt_format)}"


# `date_icon` appends the value it is given to a Text as plain text, which
# escapes whatever markup the value already carried, so one `from_markup` pass
# hands that markup back as literal text rather than dropping it. A second pass
# is what actually strips it.
def _strip_markup(value: str) -> str:
    return Text.from_markup(Text.from_markup(value).plain).plain


DATE_ICON_COMPLETED = "󰃯 "
DATE_ICON_PENDING = "󰃰 "
DATE_ICON_OVERDUE = " "


# The calendar in front of a date, so a date column is recognisable as one from
# across the row. It arrives with a status color of its own, which the color
# formatter above it then drops in favor of one style over the whole column.
def date_icon(field: str):
    @extra_formatter
    def wrapper(value: str, todo: Todo, api: DooitAPI):
        date = getattr(todo, field)

        if not date:
            return value

        theme = api.vars.theme

        if todo.is_completed:
            icon, color = DATE_ICON_COMPLETED, theme.green
        elif date < datetime.now():
            icon, color = DATE_ICON_OVERDUE, theme.red
        else:
            icon, color = DATE_ICON_PENDING, theme.yellow

        return Text() + Text.from_markup(icon, style=Style(color=color)) + value

    return wrapper


# Runs after the calendar icon has been prepended, so icon and date get one
# shared lead-time color. The icon arrives carrying its own status color, and
# "Today" its own bold red, both of which are dropped here in favor of one
# style over the whole column; the result has to be handed back as a markup
# string, since a Text would get escaped by the formatter store.
def date_color_formatter(field: str):
    @extra_formatter
    def wrapper(value: str, todo: Todo, api: DooitAPI) -> str:
        date = getattr(todo, field)

        if not date:
            return value

        theme = api.vars.theme
        now = datetime.now()
        bold = False

        if todo.is_completed:
            # Nothing is urgent about a done todo
            color = theme.green
        elif date.date() == now.date():
            # Checked ahead of the overdue branch so a todo dated today reads
            # the same whether its time has passed or is still to come: this is
            # the color for the "Today" that `due_danger_today` put in place of
            # the date, and the bold is what sets it apart from merely overdue.
            color = theme.red
            bold = True
        elif date < now:
            color = theme.red
        elif date.date() <= _add_working_days(now.date(), WORKING_DAYS_PER_WEEK):
            color = theme.yellow
        else:
            # A date nobody has to think about yet gets no color of its own,
            # only the theme's white: anything grayer would read as completed
            color = theme.foreground3

        style = f"bold {color}" if bold else color
        return f"[{style}]{_strip_markup(value)}[/]"

    return wrapper


# How many todos hang below this one, at any depth. Nesting is invisible while a
# todo is collapsed, so the count rides along with the description, in the same
# dimmed accent as the project pane's task tally.
def todo_description_formatter(description: str, todo: Todo, api: DooitAPI) -> str:
    count = todo.total_children

    if not count:
        return description

    return f"{description} [{count_color(api)}]({count})[/]"


def todo_effort_formatter(effort: int, _: Todo) -> str:
    if not effort:
        return ""

    return str(effort)


# A sheet of paper on the rows that carry a note, and nothing at all on the
# ones that do not. The column is never wider than its own header, so the icon
# marks the row without taking any room from the description.
NOTE_ICON = ""


def todo_note_formatter(note: str, _: Todo, api: DooitAPI) -> str:
    # A space rather than an empty string: the formatter store turns anything
    # falsy into a dim, centered "-", which is not the same as nothing
    if not (note or "").strip():
        return " "

    return f"[{api.vars.theme.foreground3}]{NOTE_ICON}[/]"


# Runs after the flame icon has been prepended, so icon and number come out in
# one shared color instead of the icon keeping the orange it arrives with. Same
# trick the due column uses: the result goes back as a markup string, since a
# Text would get escaped by the formatter store.
@extra_formatter
def todo_effort_color_formatter(effort: str, todo: Todo, api: DooitAPI) -> str:
    if not todo.effort:
        return effort

    return f"[{effort_color(todo.effort, api)}]{_strip_markup(effort)}[/]"


def todo_recurrence_formatter(recurrence: Optional[timedelta], _):
    if recurrence is None:
        return ""

    return Recurrence.timedelta_to_simple_string(recurrence)


# How far a completed row's text is pulled towards the background. Far enough
# that a done row sinks into the background at a glance, but short of the point
# where the description stops being readable when you go looking for it.
COMPLETED_FADE = 0.55


# A row that has been finished or thrown away is done with: its whole line is
# grayed out, and its description struck through on top of that. The status
# column is left alone, so the check mark stays the one bright thing left on
# the row.
def _gray_out(applies: Callable[[Todo], bool], strike: bool):
    @extra_formatter
    def wrapper(value: str, todo: Todo, api: DooitAPI):
        if not applies(todo):
            return

        theme = api.vars.theme

        # The colors handed out by the formatters above sit on inner spans,
        # which a base style can't override, so the value is flattened back to
        # plain text before the gray goes on.
        plain = Text.from_markup(value).plain

        # `dim` on its own is a hint that plenty of terminals ignore, so the
        # fade is baked into the color and dim just rides along on top.
        return Text(
            plain,
            style=Style(
                color=blend(theme.foreground1, theme.background1, COMPLETED_FADE),
                dim=True,
                strike=strike,
            ),
        ).markup

    return wrapper


def gray_out_completed(strike: bool = False):
    return _gray_out(lambda todo: todo.is_completed, strike)


# The Bin is read the way the completion log is, so the rows in it are drawn
# the same way: struck through and sunk into the background, because they are
# not work any more either
def gray_out_binned(strike: bool = False):
    return _gray_out(lambda todo: todo.is_binned, strike)


# The waste basket in front of the date a row was thrown away on, the same one
# the Bin itself is drawn with. It carries the muted gray the rest of the row
# is faded to rather than a status color: nothing about a binned row is urgent,
# and the date is only there to say how long ago you changed your mind.
BIN_DATE_ICON = "󰆴 "


@extra_formatter
def binned_date_formatter(value: str, todo: Todo, api: DooitAPI) -> str:
    if not todo.binned_at:
        return value

    theme = api.vars.theme
    color = blend(theme.foreground1, theme.background1, COMPLETED_FADE)

    return f"[{color}]{BIN_DATE_ICON}{_strip_markup(value)}[/]"


# Hold-to-show help


# Terminals don't report key releases, so a held "?" is detected through the
# terminal's own key auto-repeat: every repeat pushes the close back.
#
# The wait for the *first* repeat has to cover the OS repeat delay (Windows:
# up to 1s), or the menu blinks shut before the hold is noticed. Once repeats
# are streaming in (every ~30ms) a much shorter wait spots the release, so the
# menu closes snappily the moment "?" is let go.
HELP_FIRST_REPEAT_TIMEOUT = 1.0
HELP_HOLD_TIMEOUT = 0.1

_help_close_timer = None


def _close_help(api: DooitAPI):
    global _help_close_timer

    _help_close_timer = None
    if isinstance(api.app.screen, HelpScreen):
        api.app.pop_screen()


def _keep_help_open(api: DooitAPI, timeout: float = HELP_HOLD_TIMEOUT):
    global _help_close_timer

    if _help_close_timer is not None:
        _help_close_timer.stop()

    _help_close_timer = api.app.set_timer(timeout, lambda: _close_help(api))


def show_help_while_held(api: DooitAPI):
    api.show_help()
    _keep_help_open(api, HELP_FIRST_REPEAT_TIMEOUT)


# Each auto-repeat of "?" reaches the help screen itself, not the tree
HelpScreen.key_question_mark = lambda self: _keep_help_open(self.api)


# Project formatters


# Every todo nested under the project, counted at every level; sub projects
# are walked into but not counted themselves. It gets a column of its own, so
# nothing but the number is needed. The column header is drawn in the accent
# color, and the numbers under it in a dimmer shade of the same, so the pair
# reads as one unit without competing with the descriptions beside it.
def project_tasks_formatter(count: int, _: Project, api: DooitAPI) -> str:
    if not count:
        return ""

    return f"[{count_color(api)}]{count}[/]"


# The folder every stored project is drawn with, the same one the status bar
# marks the current project with. A fixed project brings an icon of its own
# instead, which is what tells the two kinds apart at a glance.
PROJECT_ICON = "󰉋"

# How far the folder is pulled towards the background: enough that a column of
# them stays quiet behind the names it marks
PROJECT_ICON_FADE = 0.35


# Runs after the sub project count has been appended, so the icon is the very
# first thing on the row whatever else the name picked up along the way. A
# fixed project takes the accent, since it is part of the app rather than one
# more thing in the list.
@extra_formatter
def project_icon_formatter(name: str, project, api: DooitAPI) -> str:
    theme = api.vars.theme

    if getattr(project, "is_fixed", False):
        icon, color = project.icon, theme.primary
    else:
        icon = PROJECT_ICON
        color = blend(theme.foreground1, theme.background1, PROJECT_ICON_FADE)

    return f"[{color}]{icon}[/] {name}"


# How far a muted project is pulled towards the background: the same fade a
# completed todo gets, and for the same reason — it is done with, and only
# looked at on purpose.
MUTED_PROJECT_FADE = COMPLETED_FADE


# A project that is never worked out of is drawn in one flat gray, icon and
# all. The accent the fixed projects otherwise carry would put it on a level
# with Today, which is where the day actually starts.
@extra_formatter
def gray_out_muted_project(value: str, project, api: DooitAPI):
    if not getattr(project, "muted", False):
        return

    theme = api.vars.theme

    # The colors handed out by the formatters above sit on inner spans, which a
    # base style can't override, so the value is flattened before the gray
    plain = Text.from_markup(value).plain

    return Text(
        plain,
        style=Style(
            color=blend(theme.foreground1, theme.background1, MUTED_PROJECT_FADE),
            dim=True,
        ),
    ).markup


# How many projects hang below this one, at any depth. Nesting is invisible
# while a project is collapsed, so the count rides along with the name, in the
# same dimmed accent as the task tally beside it.
def project_description_formatter(
    description: str, project: Project, api: DooitAPI
) -> str:
    count = project.total_projects

    if not count:
        return description

    return f"{description} [{count_color(api)}]({count})[/]"


@subscribe(Startup)
def key_setup(api: DooitAPI, _):
    # Groups show up as sections in the help screen, in this order
    NAVIGATION = "Navigation"
    EDITING = "Editing"
    PRIORITY_EFFORT = "Priority & Effort"
    MOVING = "Moving & Clipboard"
    VIEW = "Search & View"
    APP = "App"

    api.keys.set("j", api.focus_projects, group=NAVIGATION)
    api.keys.set("ö", api.focus_todos, group=NAVIGATION)
    api.keys.set("k", api.move_up, group=NAVIGATION)
    api.keys.set("l", api.move_down, group=NAVIGATION)
    api.keys.set("gg", api.go_to_top, group=NAVIGATION)
    api.keys.set("gt", api.goto_today, group=NAVIGATION)
    api.keys.set("gu", api.goto_upcoming, group=NAVIGATION)
    api.keys.set("gc", api.goto_completed, group=NAVIGATION)
    api.keys.set("gb", api.goto_bin, group=NAVIGATION)
    api.keys.set("G", api.go_to_bottom, group=NAVIGATION)
    api.keys.set("h", api.toggle_expand, group=NAVIGATION)

    api.keys.set("i", api.edit_description, group=EDITING)
    api.keys.set("d", api.edit_due, group=EDITING)
    # Lowercase, matching the other date: the sorting chords below moved up to
    # the shifted "S" to leave this one free, since a key that is the start of
    # another one can never be pressed on its own
    api.keys.set("s", api.edit_scheduled, group=EDITING)
    api.keys.set("r", api.edit_recurrence, group=EDITING)
    api.keys.set("n", api.add_sibling, group=EDITING)
    api.keys.set("N", api.add_child_node, group=EDITING)
    # The whole task in one line, from wherever the cursor happens to be. The
    # shifted twin of the key that ticks one off, since between them they are
    # the two ends of a task's life
    api.keys.set("C", api.quick_add, group=EDITING)
    api.keys.set(" ", api.show_note, group=EDITING)
    # The scratchpad, next to the key that opens a todo's note: the same
    # window, for the thoughts that have no task to be written on yet
    api.keys.set("m", api.show_pinned_note, group=EDITING)
    api.keys.set("c", api.toggle_complete, group=EDITING)
    # Throwing something away costs nothing and asks nothing: it goes to the
    # Bin, where "u" fetches it back. Getting rid of it for real is the other
    # chord, which is the one that stops to ask
    api.keys.set("xx", api.remove_node, group=EDITING)
    api.keys.set("yy", api.delete_node, group=EDITING)
    api.keys.set("u", api.restore_node, group=EDITING)
    # The shifted twin of the chord that deletes one task for good, and the
    # same thing over the whole Bin: it can be pressed from anywhere, and says
    # how much is about to go before it goes. A chord rather than the single
    # shifted key, since the whole Bin is far too much to lose to a slip of
    # the finger — it has to be typed twice over, the way "yy" does
    api.keys.set("YY", api.empty_bin, group=EDITING)

    # A scale is one thing to learn, not four, so the whole run of digits is
    # listed as the single row it reads as. The keys are still set one at a
    # time; it is only the help screen that is told to write them as a range.
    PRIORITY_LABEL = f"p0-p{max(PRIORITIES)}"
    PRIORITY_HELP = (
        f"Set the todo priority, p1 the most urgent "
        f"and p{max(PRIORITIES)} the least (p0 clears it)"
    )

    for priority in [0, *PRIORITIES]:
        api.keys.set(
            f"p{priority}",
            partial(api.set_priority, priority),
            description=PRIORITY_HELP,
            group=PRIORITY_EFFORT,
            label=PRIORITY_LABEL,
        )

    # Effort is picked off a fixed scale the same way priority is, so it is
    # typed the same way: a chord, not a text field. "e" on its own is only a
    # prefix of these, so it stays unbound and waits for the digit.
    EFFORT_LABEL = f"e0-e{max(EFFORTS)}"
    EFFORT_HELP = (
        f"Set the todo effort, e1 the quickest "
        f"and e{max(EFFORTS)} the biggest job (e0 clears it)"
    )

    for effort in [0, *EFFORTS]:
        api.keys.set(
            f"e{effort}",
            partial(api.set_effort, effort),
            description=EFFORT_HELP,
            group=PRIORITY_EFFORT,
            label=EFFORT_LABEL,
        )

    api.keys.set("L", api.shift_down, group=MOVING)
    api.keys.set("K", api.shift_up, group=MOVING)
    # A task moves sideways as well as up and down: shifted "i" files it under
    # the task above it, shifted "u" pulls it back out. Only the tasks pane
    # has levels to move between, so the projects pane leaves both alone
    api.keys.set("I", api.indent_todo, group=MOVING)
    api.keys.set("U", api.unindent_todo, group=MOVING)
    # The clipboard is the system one, so it is worked with the keys the rest
    # of the desktop uses rather than vim's
    api.keys.set("<ctrl+c>", api.copy_description_to_clipboard, group=MOVING)
    api.keys.set("<ctrl+v>", api.paste_as_sibling, group=MOVING)

    # "o" for open, on the row and inside the note alike: the same key opens
    # the link it is standing on wherever the link is written
    api.keys.set("o", api.open_link, group=VIEW)
    # "/" opens the finder over the app rather than filtering the pane in
    # front: what a search is for here is a task somewhere else in the tree,
    # and enter walks the cursor over to it
    api.keys.set("/", api.start_search, group=VIEW)
    api.keys.set("q", api.toggle_row_shading, group=VIEW)

    # The order a project is read in, typed as one chord per order: shifted
    # "S" then the shifted initial of the thing sorted by. Shifted, so that
    # plain "s" is left to the scheduled date rather than being swallowed as
    # the prefix of these. They are one row in the help for the same reason
    # the priority scale is — three ways of asking the same question, and a
    # list of them is read as a list, not as three bindings.
    SORT_LABEL = "S" + "/S".join(mode[0].upper() for mode in SORT_MODES)
    SORT_HELP = "Sort the todos by " + ", ".join(
        SORT_LABELS[mode] for mode in SORT_MODES
    )

    for mode in SORT_MODES:
        api.keys.set(
            f"S{mode[0].upper()}",
            partial(api.sort_todos, mode),
            description=SORT_HELP,
            group=VIEW,
            label=SORT_LABEL,
        )

    api.keys.set(
        "?",
        lambda: show_help_while_held(api),
        description="Show the help screen (while held)",
        group=APP,
        hidden=True,
    )
    # The one way out of dooit: ctrl+c is a copy here, as it is everywhere
    # else, and nothing else quits
    api.keys.set("<ctrl+q>", api.quit, group=APP)


@subscribe(Startup)
def layout_setup(api: DooitAPI, _):
    api.layouts.project_layout = [
        ProjectWidget.description,
        ProjectWidget.tasks,
    ]
    api.layouts.todo_layout = [
        TodoWidget.status,
        TodoWidget.description,
        # The two dates sit side by side, right after the description: the day
        # the work is planned for, then the day it is owed by, so the plan and
        # the deadline are read as the pair they are
        TodoWidget.scheduled,
        TodoWidget.due,
        TodoWidget.effort,
        TodoWidget.recurrence,
        # Last on the row: a note is something a todo either has or has not,
        # read in one glance and never scanned against the columns beside it
        TodoWidget.note,
    ]


@subscribe(Startup)
def formatter_setup(api: DooitAPI, _):
    # Added first => runs last, so the graying has the final say over every
    # color the formatters below hand out
    for gray_out in (gray_out_binned, gray_out_completed):
        api.formatter.todos.description.add(gray_out(strike=True))
        api.formatter.todos.due.add(gray_out())
        api.formatter.todos.scheduled.add(gray_out())
        api.formatter.todos.effort.add(gray_out())
        api.formatter.todos.recurrence.add(gray_out())
        api.formatter.todos.note.add(gray_out())

    api.formatter.todos.status.add(todo_status_formatter)
    api.formatter.todos.description.add(todo_description_formatter)

    # Tags and URLs are picked out of the raw description, so they have to run
    # before the child count appends its own markup: added last => runs first.
    # The link goes on ahead of the tags, so an "@" inside a URL is already
    # sealed inside the link span by the time the tag regex comes past.
    api.formatter.todos.description.add(description_highlight_tags())
    api.formatter.todos.description.add(description_highlight_link())

    # Every date column is built the same way, out of the same formatters. The
    # completion date is only ever drawn in the Completed project, where it
    # stands in for the two columns above: it comes out green throughout, since
    # the row it is on is done and nothing about it can be late any more
    for column, field in (
        (api.formatter.todos.due, "due"),
        (api.formatter.todos.scheduled, "scheduled"),
        (api.formatter.todos.completed, "completed_at"),
    ):
        column.add(todo_date_formatter)
        # Value formatters stop at the first one that returns something, so
        # this has to sit after the date formatter to get the first look: on
        # the day itself it swallows the date and puts a plain "Today" there
        # instead, and on any other day it declines and lets the date through.
        column.add(due_danger_today())
        column.add(date_color_formatter(field))
        column.add(date_icon(field))  # added last => runs first

    # The Bin's own date column, built out of the same date formatter, read a
    # day at a time the way the completion log is, and then marked and colored
    # by the one thing it has to say, which is that the row is in the Bin
    api.formatter.todos.binned.add(todo_date_formatter)
    api.formatter.todos.binned.add(due_danger_today())
    api.formatter.todos.binned.add(binned_date_formatter)

    api.formatter.todos.effort.add(todo_effort_formatter)
    api.formatter.todos.effort.add(todo_effort_color_formatter)
    # The flame is what tells a lone digit in the effort column apart from the
    # numbers elsewhere on the row; added last => runs first, so the color
    # formatter above gets to paint it in the same shade as the number.
    # Effort 0 is left as an empty column rather than a flame with nothing on it.
    api.formatter.todos.effort.add(effort_icon(show_on_zero=False))
    api.formatter.todos.note.add(todo_note_formatter)
    api.formatter.todos.recurrence.add(todo_recurrence_formatter)
    # Marks the repeating todos, whose interval is easy to miss as bare text
    api.formatter.todos.recurrence.add(recurrence_icon())

    # Added first => runs last, so the gray has the final say over the icon and
    # the counts every formatter below hands out
    api.formatter.projects.description.add(gray_out_muted_project)
    api.formatter.projects.tasks.add(gray_out_muted_project)

    # Added before the one below it => runs after it, so the icon ends up in
    # front of everything that formatter appends to the name
    api.formatter.projects.description.add(project_icon_formatter)
    api.formatter.projects.description.add(project_description_formatter)
    api.formatter.projects.tasks.add(project_tasks_formatter)


# Status bar


# The bar is a powerline: every widget paints a solid block of background, and
# the rounded caps between them belong to the block they open — drawn in that
# block's color, over the color of the block they leave behind.
ROUND_OPEN = ""
ROUND_CLOSE = ""


# What the caps at either end of a chain sit on: the bar's own background
def bar_background(api: DooitAPI) -> str:
    return api.vars.theme.background2


MODE_COLORS = {
    "NORMAL": "primary",
    "INSERT": "secondary",
}


def mode_color(api: DooitAPI, mode: str) -> str:
    theme = api.vars.theme
    return getattr(theme, MODE_COLORS.get(mode, "primary"))


# The mode block takes its color from the mode itself, so the two caps around it
# have to be repainted whenever it changes. A Powerline widget is fixed at
# startup and can't follow along, so all three pieces are built here, each one
# its own widget listening to the same event.
def mode_widget(render: Callable[[DooitAPI, str], Text]) -> StatusBarWidget:
    @subscribe(ModeChanged)
    def wrapper(api: DooitAPI, event: ModeChanged) -> Text:
        return render(api, event.mode)

    return StatusBarWidget(wrapper)


def mode_cap(glyph: str) -> StatusBarWidget:
    return mode_widget(
        lambda api, mode: Text(
            glyph,
            style=Style(color=mode_color(api, mode), bgcolor=bar_background(api)),
        )
    )


def mode_label(api: DooitAPI, mode: str) -> Text:
    return Text(
        f" {mode} ",
        style=Style(
            color=api.vars.theme.background1,
            bgcolor=mode_color(api, mode),
            bold=True,
        ),
    )


# Completion of the current project, as a meter that can be read without
# parsing the number beside it
PROGRESS_CELLS = 5
PROGRESS_FILLED = "▰"
PROGRESS_EMPTY = "▱"

# How far the unfilled cells are pulled towards the background: present enough
# to show how much meter is left, faint enough not to read as progress
PROGRESS_EMPTY_FADE = 0.6


class ProjectProgressMeter(ProjectProgress):
    def __init__(self, api: DooitAPI, fg: str = "", bg: str = "") -> None:
        # The base widget pipes its percentage through `fmt`; the meter is built
        # from that number rather than around it, so nothing is added there.
        super().__init__(api, fmt="{}", fg=fg, bg=bg)

    @property
    def value(self) -> str:
        percent = super().value
        # Empty until a project has been selected: show an empty meter rather
        # than nothing, so the segment keeps its shape and its caps
        percent = int(percent) if percent.isdigit() else 0

        theme = self.theme
        filled = round(percent * PROGRESS_CELLS / 100)
        # A finished project goes green; short of that the meter stays accent
        color = theme.green if percent == 100 else theme.primary
        empty = blend(theme.foreground1, theme.background1, PROGRESS_EMPTY_FADE)

        return (
            f" [{color}]{PROGRESS_FILLED * filled}[/]"
            f"[{empty}]{PROGRESS_EMPTY * (PROGRESS_CELLS - filled)}[/]"
            f" {percent:>3}% "
        )


@subscribe(Startup)
def bar_setup(api: DooitAPI, _):
    theme = api.vars.theme

    # The mode sits alone on the left as a pill, and everything about the
    # current project is chained to the right edge: how far along it is, what
    # it is called, how its todos stand, and the time. The chain alternates
    # between a recessed and a raised background so each segment stays its own
    # block, and ends on the accent, where the eye lands last.
    bar_widgets = [
        mode_cap(ROUND_OPEN),
        mode_widget(mode_label),
        mode_cap(ROUND_CLOSE),
        Spacer(api, width=0, bg=bar_background(api)),
        Powerline.left_rounded(api, fg=theme.background1),
        ProjectProgressMeter(api, fg=theme.foreground2, bg=theme.background1),
        Powerline.left_rounded(api, fg=theme.background3, bg=theme.background1),
        CurrentProject(
            api,
            fmt=" 󰉋 {} ",
            fg=theme.foreground3,
            bg=theme.background3,
        ),
        Powerline.left_rounded(api, fg=theme.background1, bg=theme.background3),
        # The tally borrows the tree's own checkboxes, so a count in the bar
        # and a row in the pane are recognisably the same thing
        StatusIcons(
            api,
            completed_icon=f"{CHECKBOX_TICKED} ",
            pending_icon=f"{CHECKBOX_EMPTY} ",
            overdue_icon="󰅗 ",
            bg=theme.background1,
        ),
        Powerline.left_rounded(api, fg=theme.primary, bg=theme.background1),
        Clock(
            api,
            format="%H:%M:%S",
            fmt="[bold] 󰥔 {} [/]",
            fg=theme.background1,
            bg=theme.primary,
        ),
    ]
    api.bar.set(bar_widgets)


@subscribe(Startup)
def dashboard_setup(api: DooitAPI, _):
    api.dashboard.set(
        [
            "Welcome to Dooit!",
            "",
            "If you're stuck, press '?' for help.",
        ]
    )
