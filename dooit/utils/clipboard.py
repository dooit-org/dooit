"""
The clipboard, as far as a terminal application can reach it

Two channels, because neither one covers the ground on its own: textual writes
through the terminal itself (an OSC 52 escape), which is what carries a copy
out of an ssh session or out of WSL, while pyperclip talks to the host's own
clipboard - and is the only one of the two that can *read* it back.
"""

from typing import TYPE_CHECKING, Optional

import pyperclip

if TYPE_CHECKING:  # pragma: no cover
    from textual.app import App


def running_app() -> Optional["App"]:
    """
    The app this call is running inside, for code that is handed no app

    A text field is a plain object rather than a widget: it is handed
    keystrokes and nothing else, so the only way it can reach the terminal
    channel is to ask which app it is running in.
    """

    from textual._context import active_app

    return active_app.get(None)


def copy_text(app: Optional["App"], text: str) -> None:
    """
    Put `text` on the clipboard, by both routes
    """

    app = app or running_app()

    if app is not None:
        app.copy_to_clipboard(text)

    try:
        pyperclip.copy(text)
    except Exception:
        # No clipboard tool on the host (no xclip, no clip.exe, ...). The
        # terminal was still handed the text, so the copy is not lost - and a
        # failure here is nothing the user asked about
        pass


def paste_text(app: Optional["App"] = None) -> str:
    """
    What is on the clipboard, or "" if there is nothing to be had

    Falls back to textual's own clipboard, which holds whatever dooit last
    copied, so a copy and paste inside dooit works even on a host with no
    clipboard tool at all.
    """

    app = app or running_app()

    try:
        text = str(pyperclip.paste())
    except Exception:
        text = ""

    if text:
        return text

    return app.clipboard if app is not None else ""
