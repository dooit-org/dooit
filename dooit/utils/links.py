"""
The links inside a description or a note, and the way out to a browser

Two halves that have to be kept together: what dooit *underlines* and what
dooit *opens* are read off the same scan, so a key pressed on something drawn
as a link can never come back saying there was no link there.
"""

import os
import re
from dataclasses import dataclass
from shutil import which
from subprocess import DEVNULL, Popen
from typing import List, Optional

from rich.markup import escape

# A link starts at a scheme - or at the "www." that stands in for one - and
# runs to the first character that cannot be part of it. Whitespace ends a
# URL, and so do the quotes and brackets that only ever get wrapped around one
URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"'`]+", re.IGNORECASE)

# Punctuation that ends the sentence rather than the URL. A link at the end of
# a line is written with a full stop after it far more often than a link is
# written to a path ending in one, so the trailing run is dropped. The "*" is
# in the list because a note can be holding *a link in italics*
TRAILING = ".,;:!?*)]}"

# What a closing bracket in that list is weighed against: a URL carrying a
# balanced pair - the parenthesised tail of a wiki article, say - keeps it
BRACKETS = {")": "(", "]": "[", "}": "{"}


@dataclass(frozen=True)
class Link:
    """
    One link, and where in the text it was found

    The offsets are in characters and are into the text handed to the scan,
    which is what a cursor position is measured in too.
    """

    start: int
    end: int
    url: str


def _trim(url: str) -> str:
    """
    Drop the punctuation that belongs to the sentence, not to the link
    """

    while url and url[-1] in TRAILING:
        opening = BRACKETS.get(url[-1])

        if opening is not None and url.count(opening) >= url.count(url[-1]):
            break

        url = url[:-1]

    return url


def find_links(text: str) -> List[Link]:
    """
    Every link in `text`, in the order they are written
    """

    links = []

    for match in URL_RE.finditer(text):
        found = _trim(match.group())

        # What the trim can leave behind: a bare scheme with the whole of the
        # address trimmed off it is not something to hand a browser
        if found.lower().rstrip("/") in ("http:", "https:", "www"):
            continue

        # A browser needs the scheme even where a reader does not
        url = found if "://" in found else f"https://{found}"

        links.append(Link(match.start(), match.start() + len(found), url))

    return links


def link_at(text: str, column: int) -> Optional[Link]:
    """
    The link the cursor is standing on, if it is standing on one

    The character *under* the cursor is what counts: a block cursor sitting
    one past the last character of a URL is on the space after the link, the
    same way it is everywhere else in the editor.
    """

    for link in find_links(text):
        if link.start <= column < link.end:
            return link

    return None


def first_link(text: str) -> Optional[Link]:
    """
    The link a row is opened by: the first one written in it
    """

    links = find_links(text)

    return links[0] if links else None


# How much of a URL is said back when one is opened: enough to tell two links
# on the same row apart, short enough to leave the line it is written on
LABEL_MAX = 50


def link_label(url: str) -> str:
    """
    A URL as a one-line message can carry it: shortened, and with its
    brackets escaped so a query string is not read as markup
    """

    if len(url) > LABEL_MAX:
        url = url[: LABEL_MAX - 1] + "…"

    return escape(url)


# The commands that hand a URL over to whatever the desktop opens links with,
# in the order they are tried, each with the arguments that go in front of the
# URL. The last one is what makes this work under WSL, where there is no
# xdg-open and no browser on the Linux side at all: `webbrowser` finds nothing
# there, so without it the key looks dead.
#
# It is the URL handler itself rather than `explorer.exe`, which is the
# obvious way in and the wrong one: handed a URL with a query string on it,
# explorer gives up on the address and opens a File Explorer window instead
OPENERS = (
    ("wslview", ()),
    ("xdg-open", ()),
    ("open", ()),
    ("rundll32.exe", ("url.dll,FileProtocolHandler",)),
)


def open_url(url: str) -> bool:
    """
    Hand `url` to the desktop's browser; False when nothing would take it
    """

    for name, arguments in OPENERS:
        command = which(name)

        if command is None:
            continue

        try:
            # Detached, with all three streams tied off: whatever is spawned
            # must not write into the terminal dooit is drawing in, and must
            # not keep a handle on it either
            Popen(
                [command, *arguments, url],
                stdin=DEVNULL,
                stdout=DEVNULL,
                stderr=DEVNULL,
                start_new_session=True,
            )
        except OSError:
            continue

        return True

    # Last resort, and only where there is a screen to open a window on:
    # `webbrowser` falls back to console browsers - lynx, w3m - which it runs
    # in the *foreground*, and that would take the terminal out from under
    # dooit and hang it there. With a display it hands off to a GUI browser
    # in the background instead, which is the only case worth trying
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False

    import webbrowser

    try:
        return webbrowser.open(url)
    except Exception:
        return False
