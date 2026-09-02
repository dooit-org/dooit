from datetime import date, datetime, timedelta
from functools import partial
from typing import Callable, Optional
from rich.style import Style
from dooit.api import Todo, Workspace
from dooit_extras.formatters import (
    description_highlight_link,
    description_highlight_tags,
    due_danger_today,
    due_icon,
    effort_icon,
    recurrence_icon,
)
from dooit_extras.bar_widgets import (
    Clock,
    CurrentWorkspace,
    Powerline,
    Spacer,
    StatusIcons,
    WorkspaceProgress,
)
from dooit.ui.api import DooitAPI, extra_formatter, subscribe
from dooit.ui.api.widgets import TodoWidget, WorkspaceWidget
from dooit.ui.api.events import ModeChanged, Startup
from dooit.ui.screens import HelpScreen
from dooit.ui.widgets.bars import StatusBarWidget
from dooit.ui.widgets.inputs.model_inputs import Recurrence
from dooit.utils import blend
from rich.text import Text


# Todo formatters


# The task tally on a workspace and the child count trailing a todo description
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


# German date convention: day first, dot separated, and the year always spelled
# out as its last two digits. The time only shows up when it is something other
# than midnight.
def todo_due_formatter(due: Optional[datetime], _: Todo) -> str:
    if due is None:
        return ""

    dt_format = "%d.%m.%y"

    if due.hour or due.minute:
        dt_format += " (%H:%M)"

    return due.strftime(dt_format)


# `due_icon` appends the value it is given to a Text as plain text, which
# escapes whatever markup the value already carried, so one `from_markup` pass
# hands that markup back as literal text rather than dropping it. A second pass
# is what actually strips it.
def _strip_markup(value: str) -> str:
    return Text.from_markup(Text.from_markup(value).plain).plain


# Runs after the calendar icon has been prepended, so icon and date get one
# shared lead-time color. The icon arrives carrying its own status color, and
# "Today" its own bold red, both of which are dropped here in favor of one
# style over the whole column; the result has to be handed back as a markup
# string, since a Text would get escaped by the formatter store.
@extra_formatter
def todo_due_color_formatter(due: str, todo: Todo, api: DooitAPI) -> str:
    if not todo.due:
        return due

    theme = api.vars.theme
    now = datetime.now()
    bold = False

    if todo.is_completed:
        # Nothing is urgent about a done todo
        color = theme.green
    elif todo.due.date() == now.date():
        # Checked ahead of the overdue branch so a todo due today reads the
        # same whether its time has passed or is still to come: this is the
        # color for the "Today" that `due_danger_today` put in place of the
        # date, and the bold is what sets it apart from merely overdue.
        color = theme.red
        bold = True
    elif todo.due < now:
        color = theme.red
    elif todo.due.date() <= _add_working_days(now.date(), WORKING_DAYS_PER_WEEK):
        color = theme.yellow
    else:
        color = theme.green

    style = f"bold {color}" if bold else color
    return f"[{style}]{_strip_markup(due)}[/]"


# How many todos hang below this one, at any depth. Nesting is invisible while a
# todo is collapsed, so the count rides along with the description, in the same
# dimmed accent as the workspace pane's task tally.
def todo_description_formatter(description: str, todo: Todo, api: DooitAPI) -> str:
    count = todo.total_children

    if not count:
        return description

    return f"{description} [{count_color(api)}]({count})[/]"


def todo_effort_formatter(effort: int, _: Todo) -> str:
    if not effort:
        return ""

    return str(effort)


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


# A completed todo is done with: its whole line is grayed out, and its
# description struck through on top of that. The status column is left alone,
# so the check mark stays the one bright thing left on the row.
def gray_out_completed(strike: bool = False):
    @extra_formatter
    def wrapper(value: str, todo: Todo, api: DooitAPI):
        if not todo.is_completed:
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


# Workspace formatters


# Every todo nested under the workspace, counted at every level; sub workspaces
# are walked into but not counted themselves. It gets a column of its own, so
# nothing but the number is needed. The column header is drawn in the accent
# color, and the numbers under it in a dimmer shade of the same, so the pair
# reads as one unit without competing with the descriptions beside it.
def workspace_tasks_formatter(count: int, _: Workspace, api: DooitAPI) -> str:
    if not count:
        return ""

    return f"[{count_color(api)}]{count}[/]"


# How many workspaces hang below this one, at any depth. Nesting is invisible
# while a workspace is collapsed, so the count rides along with the name, in the
# same dimmed accent as the task tally beside it.
def workspace_description_formatter(
    description: str, workspace: Workspace, api: DooitAPI
) -> str:
    count = workspace.total_workspaces

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
    # Quitting and the help key itself need no explaining, so this group is
    # bound but hidden: it never gets a section in the help screen
    APP = "App"

    api.keys.set("j", api.focus_workspaces, group=NAVIGATION)
    api.keys.set("ö", api.focus_todos, group=NAVIGATION)
    api.keys.set("k", api.move_up, group=NAVIGATION)
    api.keys.set("l", api.move_down, group=NAVIGATION)
    api.keys.set("gg", api.go_to_top, group=NAVIGATION)
    api.keys.set("G", api.go_to_bottom, group=NAVIGATION)
    api.keys.set("h", api.toggle_expand, group=NAVIGATION)

    api.keys.set("i", api.edit_description, group=EDITING)
    api.keys.set("d", api.edit_due, group=EDITING)
    api.keys.set("r", api.edit_recurrence, group=EDITING)
    api.keys.set("a", api.add_sibling, group=EDITING)
    api.keys.set("A", api.add_child_node, group=EDITING)
    api.keys.set("c", api.toggle_complete, group=EDITING)
    api.keys.set("xx", api.remove_node, group=EDITING)

    for priority in PRIORITIES:
        api.keys.set(
            f"p{priority}",
            partial(api.set_priority, priority),
            description=f"Set the todo priority to p{priority}",
            group=PRIORITY_EFFORT,
        )

    api.keys.set(
        "p0",
        partial(api.set_priority, 0),
        description="Clear the priority of the todo",
        group=PRIORITY_EFFORT,
    )

    # Effort is picked off a fixed scale the same way priority is, so it is
    # typed the same way: a chord, not a text field. "e" on its own is only a
    # prefix of these, so it stays unbound and waits for the digit.
    for effort in EFFORTS:
        api.keys.set(
            f"e{effort}",
            partial(api.set_effort, effort),
            description=f"Set the todo effort to e{effort}",
            group=PRIORITY_EFFORT,
        )

    api.keys.set(
        "e0",
        partial(api.set_effort, 0),
        description="Clear the effort of the todo",
        group=PRIORITY_EFFORT,
    )

    api.keys.set("J", api.shift_down, group=MOVING)
    api.keys.set("K", api.shift_up, group=MOVING)
    api.keys.set("y", api.copy_description_to_clipboard, group=MOVING)
    api.keys.set("Y", api.copy_model, group=MOVING)
    # "p" is a prefix of the priority keys above, so paste lives on v/V
    api.keys.set("v", api.paste_model_below, group=MOVING)
    api.keys.set("V", api.paste_model_above, group=MOVING)

    api.keys.set("/", api.start_search, group=VIEW)
    api.keys.set("q", api.toggle_row_shading, group=VIEW)

    api.keys.set(
        "?",
        lambda: show_help_while_held(api),
        description="Show the help screen (while held)",
        group=APP,
        hidden=True,
    )
    api.keys.set("<ctrl+q>", api.quit, group=APP, hidden=True)


@subscribe(Startup)
def layout_setup(api: DooitAPI, _):
    api.layouts.workspace_layout = [
        WorkspaceWidget.description,
        WorkspaceWidget.tasks,
    ]
    api.layouts.todo_layout = [
        TodoWidget.status,
        TodoWidget.description,
        TodoWidget.effort,
        TodoWidget.due,
        TodoWidget.recurrence,
    ]


@subscribe(Startup)
def formatter_setup(api: DooitAPI, _):
    # Added first => runs last, so the graying has the final say over every
    # color the formatters below hand out
    api.formatter.todos.description.add(gray_out_completed(strike=True))
    api.formatter.todos.due.add(gray_out_completed())
    api.formatter.todos.effort.add(gray_out_completed())
    api.formatter.todos.recurrence.add(gray_out_completed())

    api.formatter.todos.status.add(todo_status_formatter)
    api.formatter.todos.description.add(todo_description_formatter)

    # Tags and URLs are picked out of the raw description, so they have to run
    # before the child count appends its own markup: added last => runs first.
    # The link goes on ahead of the tags, so an "@" inside a URL is already
    # sealed inside the link span by the time the tag regex comes past.
    api.formatter.todos.description.add(description_highlight_tags())
    api.formatter.todos.description.add(description_highlight_link())

    api.formatter.todos.due.add(todo_due_formatter)
    # Value formatters stop at the first one that returns something, so this
    # has to sit after the date formatter to get the first look: on the day a
    # todo is due it swallows the date and puts a plain "Today" there instead,
    # and on any other day it declines and lets the date through.
    api.formatter.todos.due.add(due_danger_today())
    api.formatter.todos.due.add(todo_due_color_formatter)
    api.formatter.todos.due.add(due_icon())  # added last => runs first
    api.formatter.todos.effort.add(todo_effort_formatter)
    api.formatter.todos.effort.add(todo_effort_color_formatter)
    # The flame is what tells a lone digit in the effort column apart from the
    # numbers elsewhere on the row; added last => runs first, so the color
    # formatter above gets to paint it in the same shade as the number.
    # Effort 0 is left as an empty column rather than a flame with nothing on it.
    api.formatter.todos.effort.add(effort_icon(show_on_zero=False))
    api.formatter.todos.recurrence.add(todo_recurrence_formatter)
    # Marks the repeating todos, whose interval is easy to miss as bare text
    api.formatter.todos.recurrence.add(recurrence_icon())

    api.formatter.workspaces.description.add(workspace_description_formatter)
    api.formatter.workspaces.tasks.add(workspace_tasks_formatter)


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


# Completion of the current workspace, as a meter that can be read without
# parsing the number beside it
PROGRESS_CELLS = 5
PROGRESS_FILLED = "▰"
PROGRESS_EMPTY = "▱"

# How far the unfilled cells are pulled towards the background: present enough
# to show how much meter is left, faint enough not to read as progress
PROGRESS_EMPTY_FADE = 0.6


class WorkspaceProgressMeter(WorkspaceProgress):
    def __init__(self, api: DooitAPI, fg: str = "", bg: str = "") -> None:
        # The base widget pipes its percentage through `fmt`; the meter is built
        # from that number rather than around it, so nothing is added there.
        super().__init__(api, fmt="{}", fg=fg, bg=bg)

    @property
    def value(self) -> str:
        percent = super().value
        # Empty until a workspace has been selected: show an empty meter rather
        # than nothing, so the segment keeps its shape and its caps
        percent = int(percent) if percent.isdigit() else 0

        theme = self.theme
        filled = round(percent * PROGRESS_CELLS / 100)
        # A finished workspace goes green; short of that the meter stays accent
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
    # current workspace is chained to the right edge: how far along it is, what
    # it is called, how its todos stand, and the time. The chain alternates
    # between a recessed and a raised background so each segment stays its own
    # block, and ends on the accent, where the eye lands last.
    bar_widgets = [
        mode_cap(ROUND_OPEN),
        mode_widget(mode_label),
        mode_cap(ROUND_CLOSE),
        Spacer(api, width=0, bg=bar_background(api)),
        Powerline.left_rounded(api, fg=theme.background1),
        WorkspaceProgressMeter(api, fg=theme.foreground2, bg=theme.background1),
        Powerline.left_rounded(api, fg=theme.background3, bg=theme.background1),
        CurrentWorkspace(
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
