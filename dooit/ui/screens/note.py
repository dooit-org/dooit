import re
from typing import Iterator, Optional, Tuple

from rich.style import Style
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.timer import Timer
from textual.widgets import Static, TextArea
from textual.widgets.text_area import TextAreaTheme

from dooit.api import Todo
from dooit.api.theme import DooitThemeBase
from dooit.utils import blend

from .base import BaseScreen


# Bullets are stored as the glyph itself rather than a "- " swapped out at
# render time: a TextArea draws exactly the text it holds, so a marker can
# never stand in for a different character without the columns drifting apart
BULLET = "• "

# What the styled spans are tagged with; the theme below maps them to styles
BOLD = "note-bold"
ITALIC = "note-italic"
MARKER = "note-marker"
BULLET_SPAN = "note-bullet"

# `**bold**` wins over `*italic*` by sitting first in the alternation
MARKUP_RE = re.compile(r"\*\*(?P<bold>[^*]+)\*\*|\*(?P<italic>[^*]+)\*")
BULLET_RE = re.compile(r"^[ \t]*(• )")

# How far the `*` markers are pulled towards the background: still there to be
# seen and deleted, but out of the way of the words they wrap
MARKER_FADE = 0.6

THEME_NAME = "dooit-note"

# How long the editor has to sit still before the note is written back
SAVE_DEBOUNCE = 0.4

# How much of the todo's description the window title carries
TITLE_MAX = 60


def scan_markup(line: str) -> Iterator[Tuple[int, int, str]]:
    """
    The styled spans of one line, measured in UTF-8 bytes

    `TextArea.render_line` maps the offsets it is handed back through a
    byte-to-codepoint table, so anything counted in characters would land in
    the wrong place on a line holding an umlaut - or a bullet.
    """

    def byte(index: int) -> int:
        return len(line[:index].encode("utf-8"))

    bullet = BULLET_RE.match(line)
    if bullet:
        yield byte(bullet.start(1)), byte(bullet.end(1)), BULLET_SPAN

    for match in MARKUP_RE.finditer(line):
        if match.group("bold") is not None:
            name, width = BOLD, 2
        else:
            name, width = ITALIC, 1

        start, end = match.start(), match.end()

        # The words first and the markers over the top: the spans are applied
        # in the order they are handed over
        yield byte(start + width), byte(end - width), name
        yield byte(start), byte(start + width), MARKER
        yield byte(end - width), byte(end), MARKER


def build_theme(theme: DooitThemeBase) -> TextAreaTheme:
    """
    The editor painted in the dooit theme rather than a TextArea default
    """

    marker = blend(theme.foreground1, theme.background2, MARKER_FADE)

    return TextAreaTheme(
        name=THEME_NAME,
        base_style=Style(color=theme.foreground3, bgcolor=theme.background2),
        cursor_style=Style(color=theme.background1, bgcolor=theme.primary),
        # The window is one block of text; a highlighted line would only cut
        # it in two
        cursor_line_style=Style(),
        selection_style=Style(bgcolor=theme.background3),
        syntax_styles={
            BOLD: Style(bold=True, color=theme.foreground1),
            ITALIC: Style(italic=True),
            MARKER: Style(color=marker),
            BULLET_SPAN: Style(color=theme.primary, bold=True),
        },
    )


class NoteEditor(TextArea):
    """
    A plain text editor that styles `**bold**`, `*italic*` and bullets as typed
    """

    BINDINGS = [
        Binding("ctrl+b", "wrap('**')", "Bold", show=False),
        # Two spellings of the same keystroke. A terminal that speaks the kitty
        # protocol reports `ctrl+i` as itself; every other one sends a plain
        # tab, and textual expands aliases on the binding rather than on the
        # event, so `tab` has to be named here as well to catch it. Nothing is
        # given up for it: this window holds one focusable widget, so a real
        # tab has nowhere to move the focus to anyway.
        Binding("ctrl+i", "wrap('*')", "Italic", show=False),
        Binding("tab", "wrap('*')", "Italic", show=False),
        Binding("ctrl+l", "toggle_bullet", "Bullet", show=False),
        # Takes the key off TextArea, where it deletes the character to the
        # right of the cursor; here the whole note goes, after a y/N
        Binding("ctrl+d", "clear_note", "Clear the note", show=False),
    ]

    def __init__(self, text: str) -> None:
        # `tab_behavior` stays at its default of "focus", which is what lets
        # `escape` bubble up to the screen instead of being swallowed here
        super().__init__(text)

    def _build_highlight_map(self) -> None:
        """
        Fill the map `render_line` styles from, out of our own markers

        Upstream fills it from a tree-sitter query; there is no parser for a
        markup this small, and none installed either, so the scan below stands
        in for one. Everything downstream of the map is left alone.
        """

        self._line_cache.clear()
        highlights = self._highlights
        highlights.clear()

        for row, line in enumerate(self.document.lines):
            for start, end, name in scan_markup(line):
                highlights[row].append((start, end, name))

    def action_wrap(self, marker: str) -> None:
        """
        Put `marker` either side of the selection, or take it away again
        """

        start, end = sorted(self.selection)
        selected = self.selected_text

        if not selected:
            # Nothing picked out: drop an empty pair in and sit between them
            row, column = self.cursor_location
            self.insert(marker * 2, (row, column))
            self.move_cursor((row, column + len(marker)))
            return

        wrapped = (
            selected.startswith(marker)
            and selected.endswith(marker)
            and len(selected) > 2 * len(marker)
        )

        if wrapped:
            self.replace(selected[len(marker) : -len(marker)], start, end)
        else:
            self.replace(marker + selected + marker, start, end)

    def action_toggle_bullet(self) -> None:
        """
        Put a bullet at the head of the current line, or take it away again
        """

        row, column = self.cursor_location
        line = self.document[row]
        match = BULLET_RE.match(line)

        if match:
            self.replace("", (row, match.start(1)), (row, match.end(1)))
            self.move_cursor((row, max(match.start(1), column - len(BULLET))))
            return

        indent = len(line) - len(line.lstrip(" \t"))
        self.insert(BULLET, (row, indent))
        self.move_cursor((row, column + len(BULLET)))

    @property
    def note_screen(self) -> "NoteScreen":
        screen = self.screen

        assert isinstance(screen, NoteScreen)
        return screen

    def action_clear_note(self) -> None:
        """
        Offer to throw the whole note away; the screen puts the question
        """

        self.note_screen.request_clear()

    async def _on_key(self, event: events.Key) -> None:
        """
        Carry a bullet list on to the next line, the way a list gets written
        """

        if self.note_screen.awaiting_clear:
            # The editor keeps the keyboard while the question stands, so the
            # answer arrives here rather than at a binding on the screen - and
            # is swallowed either way, so a `y` is an answer and not a letter
            event.stop()
            event.prevent_default()
            self.note_screen.answer_clear(event.key)
            return

        if event.key == "enter" and not self.read_only:
            row, _ = self.cursor_location
            line = self.document[row]
            match = BULLET_RE.match(line)

            if match:
                event.stop()
                event.prevent_default()

                if line[match.end(1) :].strip():
                    self.insert(
                        "\n" + line[: match.end(1)],
                        maintain_selection_offset=False,
                    )
                else:
                    # An empty bullet is where the list ends: the bullet goes,
                    # rather than another one arriving underneath it
                    self.replace("", (row, match.start(1)), (row, len(line)))
                    self.move_cursor((row, match.start(1)))

                return

        await super()._on_key(event)


class NoteScreen(BaseScreen):
    """
    The note of one todo, in a window over the whole screen
    """

    DEFAULT_CSS = """
    NoteScreen {
        align: center middle;

        & > NoteEditor {
            width: 70%;
            height: 60%;
        }

        & > #note-hint {
            width: 70%;
            padding: 0 2;
        }
    }
    """

    BINDINGS = [
        ("escape", "close", "Close the note"),
    ]

    HINT = (
        "ctrl+b bold    ctrl+i italic    ctrl+l bullet    "
        "ctrl+d clear    esc close"
    )

    # Worded and escaped the way the confirm bar words a deletion elsewhere in
    # dooit, so the answer is the one the user already knows
    CLEAR_PROMPT = r"Clear the whole note? \[y/N]"

    def __init__(self, todo: Todo) -> None:
        super().__init__()
        self.todo = todo
        self._save_timer: Optional[Timer] = None
        self._awaiting_clear = False

    @property
    def editor(self) -> NoteEditor:
        return self.query_one(NoteEditor)

    @property
    def hint(self) -> Static:
        return self.query_one("#note-hint", Static)

    @property
    def awaiting_clear(self) -> bool:
        return self._awaiting_clear

    @property
    def title_text(self) -> str:
        """
        Whose note this is, so the window is not just a box of text
        """

        description = self.todo.description.strip() or "Note"

        if len(description) > TITLE_MAX:
            description = description[: TITLE_MAX - 1] + "…"

        return description

    def compose(self) -> ComposeResult:
        editor = NoteEditor(self.todo.note or "")
        editor.border_title = self.title_text

        yield editor
        yield Static(self.HINT, id="note-hint")

    def on_mount(self) -> None:
        editor = self.editor
        editor.register_theme(build_theme(self.api.vars.theme))
        editor.theme = THEME_NAME

        # Focusing the editor is what "insert mode" means here: the window
        # takes the keyboard, and typing lands in the note straight away
        editor.focus()

    @on(TextArea.Changed)
    def schedule_save(self, _: TextArea.Changed) -> None:
        if self._save_timer is not None:
            self._save_timer.stop()

        self._save_timer = self.set_timer(SAVE_DEBOUNCE, self.save)

    def save(self) -> None:
        self._save_timer = None

        if self.todo.note == self.editor.text:
            return

        self.todo.note = self.editor.text
        self.todo.save()

    def request_clear(self) -> None:
        """
        Put the question up, in place of the hint line
        """

        # Nothing to lose, nothing to ask about
        if not self.editor.text or self._awaiting_clear:
            return

        self._awaiting_clear = True
        self.hint.update(self.CLEAR_PROMPT)
        self.hint.add_class("confirming")

    def answer_clear(self, key: str) -> None:
        """
        Anything but a `y` leaves the note exactly where it is
        """

        self._awaiting_clear = False
        self.hint.update(self.HINT)
        self.hint.remove_class("confirming")

        if key.lower() != "y":
            return

        self.editor.clear()

        # The debounce would get here on its own; writing it out now means the
        # row behind the window is right the moment the window closes
        self.save()

    def action_close(self) -> None:
        if self._save_timer is not None:
            self._save_timer.stop()

        # Written out here as well as on the timer, so the last keystrokes
        # can't be lost inside the debounce window
        self.save()

        # `dismiss`, not `pop_screen`: popping throws the callback the screen
        # was pushed with away without running it, and that callback is what
        # redraws the row - so the note icon would not turn up until dooit was
        # restarted
        self.dismiss()
