from datetime import datetime

from rich.text import Text


def mode(**kwargs):
    return Text("")


def clock(**kwargs):
    fmt = kwargs.get("format", "%H:%M")
    return Text(datetime.now().strftime(fmt))


def user(**kwargs):
    return Text("")


def qoute(**kwargs):
    return Text("")


def ascii(**kwargs):
    return Text("")


def current_workspace(**kwargs):
    return Text("")


def platform(**kwargs):
    return Text("")


def spacer(**kwargs):
    return Text("")


def text(**kwargs):
    return Text("")


def ticker(**kwargs):
    return Text("")
