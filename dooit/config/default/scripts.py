import getpass
import platform as platform_module
import random
from datetime import datetime

from rich.style import Style
from rich.text import Text

from dooit.ui.bridge.events import ModeChanged, TimerEvent

QUOTES = [
    "The only way to do great work is to love what you do.",
    "Simplicity is the ultimate sophistication.",
    "Talk is cheap. Show me the code.",
    "First, solve the problem. Then, write the code.",
    "Code is like humor. When you have to explain it, it's bad.",
    "Any fool can write code that a computer can understand.",
    "Premature optimization is the root of all evil.",
    "Programs must be written for people to read.",
    "The best error message is the one that never shows up.",
    "Make it work, make it right, make it fast.",
]

DOOIT_ASCII = r"""
     _             _ _
  __| | ___   ___ (_) |_
 / _` |/ _ \ / _ \| | __|
| (_| | (_) | (_) | | |_
 \__,_|\___/ \___/|_|\__|
""".strip()


def build_style(css: dict) -> Style:
    """Convert a config CSS dict to a Rich Style."""
    return Style(
        color=css.get("color"),
        bgcolor=css.get("background"),
        bold=css.get("bold"),
        italic=css.get("italic"),
    )


def small_pad(**kwargs):
    return Text(" ")


def mode(event: ModeChanged, context):
    mode = event.mode.lower()
    if mode not in context:
        return Text("")

    settings = context[event.mode.lower()]
    fmt = settings["format"]
    return Text(fmt, style=build_style(settings["css"]))


def clock(event: TimerEvent, context):
    fmt = context["format"]
    text = datetime.now().strftime(fmt)
    return Text(text, style=build_style(context["css"]))


def user(event: TimerEvent, context):
    fmt = context["format"]
    username = getpass.getuser()
    text = fmt.format(username=username)
    return Text(text, style=build_style(context["css"]))


def qoute(**kwargs):
    fmt = kwargs.get("format", "{qoute}")
    quote = random.choice(QUOTES)
    return Text(fmt.format(qoute=quote))


def ascii(**kwargs):
    fmt = kwargs.get("format", "{ascii_art}")
    return Text(fmt.format(ascii_art=DOOIT_ASCII))


def current_workspace(**kwargs):
    return Text("")


def platform(**kwargs):
    fmt = kwargs.get("format", "{platform}")
    info = f"{platform_module.system()} {platform_module.release()}"
    return Text(fmt.format(platform=info))


def spacer(**kwargs):
    return Text("")


def text(**kwargs):
    content = kwargs.get("content", "")
    return Text(str(content))


def ticker(**kwargs):
    return Text("")
