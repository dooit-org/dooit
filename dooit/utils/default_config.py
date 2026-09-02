from datetime import date, datetime, timedelta
from functools import partial
import os
from typing import Optional
from rich.style import Style
from dooit.api import Todo, Workspace
from dooit_extras.formatters import due_icon
from dooit.ui.api import DooitAPI, extra_formatter, subscribe, timer
from dooit.ui.api.widgets import TodoWidget, WorkspaceWidget
from dooit.ui.api.events import ModeChanged, Startup
from dooit.ui.screens import HelpScreen
from dooit.ui.widgets.bars import StatusBarWidget
from dooit.ui.widgets.inputs.model_inputs import Recurrence
from dooit.utils import blend
from rich.text import Text


@subscribe(ModeChanged)
def get_mode(api: DooitAPI, event: ModeChanged):
    theme = api.vars.theme
    mode = event.mode

    MODES = {
        "NORMAL": theme.primary,
        "INSERT": theme.secondary,
    }

    return Text(
        f" {mode} ",
        style=Style(
            color=theme.background1,
            bgcolor=MODES.get(mode, theme.primary),
        ),
    )


@timer(1)
def get_clock(api: DooitAPI):
    theme = api.vars.theme
    time = datetime.now().strftime("%H:%M:%S")
    return Text(
        f" {time} ",
        style=Style(
            color=theme.background1,
            bgcolor=theme.secondary,
        ),
    )


@subscribe(Startup)
def get_user(api: DooitAPI, _: Startup):
    theme = api.vars.theme
    try:
        username = os.getlogin()
    except OSError:
        uid = os.getuid()
        import pwd

        username = pwd.getpwuid(uid).pw_name
    return Text(
        f" {username} ",
        style=Style(
            color=theme.background1,
            bgcolor=theme.secondary,
        ),
    )


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
        3: theme.green,
    }

    # Nothing prioritized: a gray sitting halfway between text and background
    return colors.get(priority, blend(theme.foreground1, theme.background1, 0.5))


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


# Runs after the calendar icon has been prepended, so icon and date get one
# shared lead-time color. The icon arrives carrying its own status color, which
# is dropped here; the result has to be handed back as a markup string, since a
# Text would get escaped by the formatter store.
@extra_formatter
def todo_due_color_formatter(due: str, todo: Todo, api: DooitAPI) -> str:
    if not todo.due:
        return due

    theme = api.vars.theme
    now = datetime.now()

    if todo.is_completed:
        # Nothing is urgent about a done todo
        color = theme.green
    elif todo.due < now:
        color = theme.red
    elif todo.due.date() <= _add_working_days(now.date(), WORKING_DAYS_PER_WEEK):
        color = theme.yellow
    else:
        color = theme.green

    return f"[{color}]{Text.from_markup(due).plain}[/{color}]"


# How many todos hang below this one, at any depth. Nesting is invisible while a
# todo is collapsed, so the count rides along with the description, in the same
# dimmed accent as the workspace pane's task tally.
def todo_description_formatter(description: str, todo: Todo, api: DooitAPI) -> str:
    count = todo.total_children

    if not count:
        return description

    return f"{description} [{count_color(api)}]({count})[/]"


def todo_effort_formatter(effort, _):
    if not effort:
        return ""

    return str(effort)


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
    api.keys.set("j", api.focus_workspaces)
    api.keys.set("ö", api.focus_todos)
    api.keys.set("k", api.move_up)
    api.keys.set("l", api.move_down)
    api.keys.set("i", api.edit_description)
    api.keys.set("d", api.edit_due)
    api.keys.set("r", api.edit_recurrence)
    api.keys.set("e", api.edit_effort)
    api.keys.set("a", api.add_sibling)
    api.keys.set("z", api.toggle_expand)
    api.keys.set("Z", api.toggle_expand_parent)
    api.keys.set("gg", api.go_to_top)
    api.keys.set("G", api.go_to_bottom)
    api.keys.set("A", api.add_child_node)
    api.keys.set("J", api.shift_down)
    api.keys.set("K", api.shift_up)
    api.keys.set("xx", api.remove_node)
    api.keys.set("y", api.copy_description_to_clipboard)
    api.keys.set("Y", api.copy_model)
    # "p" is a prefix of the priority keys below, so paste lives on v/V
    api.keys.set("v", api.paste_model_below)
    api.keys.set("V", api.paste_model_above)
    api.keys.set("c", api.toggle_complete)

    for priority in PRIORITIES:
        api.keys.set(
            f"p{priority}",
            partial(api.set_priority, priority),
            description=f"Set the todo priority to p{priority}",
        )

    api.keys.set(
        "p0",
        partial(api.set_priority, 0),
        description="Clear the priority of the todo",
    )

    api.keys.set("/", api.start_search)
    api.keys.set("<ctrl+s>", api.start_sort)
    api.keys.set("<ctrl+q>", api.quit)
    api.keys.set(
        "?",
        lambda: show_help_while_held(api),
        description="Show the help screen (while held)",
    )


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
    api.formatter.todos.due.add(todo_due_formatter)
    api.formatter.todos.due.add(todo_due_color_formatter)
    api.formatter.todos.due.add(due_icon())  # added last => runs first
    api.formatter.todos.effort.add(todo_effort_formatter)
    api.formatter.todos.recurrence.add(todo_recurrence_formatter)

    api.formatter.workspaces.description.add(workspace_description_formatter)
    api.formatter.workspaces.tasks.add(workspace_tasks_formatter)


@subscribe(Startup)
def bar_setup(api: DooitAPI, _):
    bar_widgets = [
        StatusBarWidget(get_mode),
        StatusBarWidget(lambda: "", width=0),
        StatusBarWidget(get_clock),
        StatusBarWidget(lambda: " ", width=1),
        StatusBarWidget(get_user),
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
