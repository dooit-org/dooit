from datetime import datetime, timedelta
import os
from typing import Optional
from rich.style import Style
from dooit.api import Todo
from dooit.ui.api import DooitAPI, subscribe, timer
from dooit.ui.api.widgets import TodoWidget, WorkspaceWidget
from dooit.ui.api.events import ModeChanged, Startup
from dooit.ui.screens import HelpScreen
from dooit.ui.widgets.bars import StatusBarWidget
from dooit.ui.widgets.inputs.model_inputs import Recurrence
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


def todo_status_formatter(status: str, _: Todo, api: DooitAPI):
    text = "o"
    theme = api.vars.theme

    color = theme.yellow

    if status == "completed":
        text = "x"
        color = theme.green

    if status == "overdue":
        text = "!"
        color = theme.red

    return Text(text, style=Style(color=color, bold=True))


def todo_due_formatter(due, _):
    if due is None:
        return ""

    text = due.strftime("%Y-%m-%d")

    if due.hour:
        text += f" ({due.strftime('%H:%M')})"

    return text


def todo_urgency_formatter(urgency, _, api: DooitAPI):
    if urgency == 0:
        return ""

    theme = api.vars.theme
    colors = {
        1: theme.green,
        2: theme.yellow,
        3: theme.orange,
        4: theme.red,
    }

    return Text(
        f"!{urgency}",
        style="bold " + colors.get(urgency, theme.primary),
    )


def todo_recurrence_formatter(recurrence: Optional[timedelta], _):
    if recurrence is None:
        return ""

    return Recurrence.timedelta_to_simple_string(recurrence)


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
    api.keys.set("p", api.paste_model_below)
    api.keys.set("P", api.paste_model_above)
    api.keys.set("c", api.toggle_complete)
    api.keys.set(["=", "+"], api.increase_urgency)
    api.keys.set(["-", "_"], api.decrease_urgency)
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
    api.layouts.workspace_layout = [WorkspaceWidget.description]
    api.layouts.todo_layout = [
        TodoWidget.status,
        TodoWidget.description,
        TodoWidget.due,
        TodoWidget.urgency,
    ]


@subscribe(Startup)
def formatter_setup(api: DooitAPI, _):
    api.formatter.todos.status.add(todo_status_formatter)
    api.formatter.todos.due.add(todo_due_formatter)
    api.formatter.todos.urgency.add(todo_urgency_formatter)
    api.formatter.todos.recurrence.add(todo_recurrence_formatter)


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
