import getpass
import platform as platform_module
import random
from datetime import datetime
from typing import TYPE_CHECKING

from rich.style import Style
from rich.text import Text

if TYPE_CHECKING:
    from dooit.ui.bridge.events import ModeChanged

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


def _build_style(css: dict) -> Style:
    """Convert a config CSS dict to a Rich Style."""
    return Style(
        color=css.get("color"),
        bgcolor=css.get("background"),
        bold=css.get("bold"),
        italic=css.get("italic"),
    )


def mode(event: "ModeChanged", **kwargs):
    mode_name = event.mode.lower()

    mode_config = kwargs.get(mode_name, {})
    global_css = kwargs.get("css", {})
    padding = int(global_css.get("padding", 0)) if isinstance(global_css, dict) else 0
    pad = " " * padding

    if isinstance(mode_config, dict):
        fmt = mode_config.get("format", mode_name.upper())
        css = mode_config.get("css", {})
        style = _build_style(css) if isinstance(css, dict) else Style()
        return Text(f"{pad}{fmt}{pad}", style=style)

    return Text(f"{pad}{mode_name.upper()}{pad}")


def clock(**kwargs):
    fmt = kwargs.get("format", "%H:%M")
    return Text(datetime.now().strftime(fmt))


def user(**kwargs):
    fmt = kwargs.get("format", "{username}")
    username = getpass.getuser()
    return Text(fmt.format(username=username))


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
