"""
The clipboard, as far as a terminal application can reach it

Two channels, because neither one covers the ground on its own: textual writes
through the terminal itself (an OSC 52 escape), which is what carries a copy
out of an ssh session or out of WSL, while pyperclip talks to the host's own
clipboard - and is the only one of the two that can *read* it back.
"""

from typing import TYPE_CHECKING

import pyperclip

if TYPE_CHECKING:  # pragma: no cover
    from textual.app import App


def copy_text(app: "App", text: str) -> None:
    """
    Put `text` on the clipboard, by both routes
    """

    app.copy_to_clipboard(text)

    try:
        pyperclip.copy(text)
    except Exception:
        # No clipboard tool on the host (no xclip, no clip.exe, ...). The
        # terminal was still handed the text, so the copy is not lost - and a
        # failure here is nothing the user asked about
        pass


def paste_text(app: "App") -> str:
    """
    What is on the clipboard, or "" if there is nothing to be had

    Falls back to textual's own clipboard, which holds whatever dooit last
    copied, so a copy and paste inside dooit works even on a host with no
    clipboard tool at all.
    """

    try:
        text = str(pyperclip.paste())
    except Exception:
        text = ""

    return text or app.clipboard
