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
from dooit.utils import (
    blend,
    copy_text,
    find_links,
    link_at,
    link_label,
    open_url,
    paste_text,
)

from .base import BaseScreen


# Bullets are stored as the glyph itself rather than a "- " swapped out at
# render time: a TextArea draws exactly the text it holds, so a marker can
# never stand in for a different character without the columns drifting apart
BULLET = "• "

# A header is the help window's section break brought into the note: a title
# with a rule drawn across underneath it. Stored as the glyph for the same
# reason the bullet is, and kept on a line of its own rather than sized to the
# words, so that retyping the title can never leave the rule the wrong length
RULE = "─"

# How wide the rule is drawn, before a narrow window is allowed to shorten it.
# Long enough to read as a divider, short enough not to wrap in a small note
HEADER_WIDTH = 40

# What the styled spans are tagged with; the theme below maps them to styles
BOLD = "note-bold"
ITALIC = "note-italic"
MARKER = "note-marker"
BULLET_SPAN = "note-bullet"
RULE_SPAN = "note-rule"
HEADER = "note-header"
LINK = "note-link"

# `**bold**` wins over `*italic*` by sitting first in the alternation
MARKUP_RE = re.compile(r"\*\*(?P<bold>[^*]+)\*\*|\*(?P<italic>[^*]+)\*")
BULLET_RE = re.compile(r"^[ \t]*(• )")

# A line that is nothing but rule. Three is the shortest run that reads as one
# on purpose rather than as a stray character
RULE_RE = re.compile(rf"^{RULE}{{3,}}[ \t]*$")

# How far the `*` markers are pulled towards the background: still there to be
# seen and deleted, but out of the way of the words they wrap
MARKER_FADE = 0.6

THEME_NAME = "dooit-note"

# How long the editor has to sit still before the note is written back
SAVE_DEBOUNCE = 0.4

# How long a message stands in the hint line before the hints come back
REPORT_TIMEOUT = 3

# How much of the todo's description the window title carries
TITLE_MAX = 60

# What the note is doing with the keyboard. The two names are the ones the
# status bar already uses out on the trees, because they mean the same thing
# here: NORMAL reads and moves around, INSERT types
MODE_NORMAL = "NORMAL"
MODE_INSERT = "INSERT"

# The motions NORMAL mode answers to. The four movement keys are dooit's own
# rather than vim's - `j`/`ö` step left and right, `k`/`l` up and down - so the
# note is walked with the same fingers as the trees behind it
NORMAL_MOTIONS = {
    "j": "cursor_left",
    "ö": "cursor_right",
    "k": "cursor_up",
    "l": "cursor_down",
    "w": "cursor_word_right",
    "b": "cursor_word_left",
    "0": "cursor_line_start",
    "$": "cursor_line_end",
}

# The keys that drop into INSERT, each landing the cursor somewhere different
INSERT_ENTRIES = ("i", "a", "I", "A")


def scan_markup(line: str, following: str = "") -> Iterator[Tuple[int, int, str]]:
    """
    The styled spans of one line, measured in UTF-8 bytes

    `TextArea.render_line` maps the offsets it is handed back through a
    byte-to-codepoint table, so anything counted in characters would land in
    the wrong place on a line holding an umlaut - or a bullet.

    `following` is the line below, which is all a header needs to be
    recognised: the rule is what says the words above it are a title.
    """

    def byte(index: int) -> int:
        return len(line[:index].encode("utf-8"))

    if RULE_RE.match(line):
        yield 0, byte(len(line)), RULE_SPAN
        return

    if RULE_RE.match(following) and line.strip():
        # The whole line is the header, and that is the end of it: a title is
        # already as loud as the window can draw it, so bold and bullets
        # inside one would be markers with nothing left to mark
        yield 0, byte(len(line)), HEADER
        return

    bullet = BULLET_RE.match(line)
    if bullet:
        yield byte(bullet.start(1)), byte(bullet.end(1)), BULLET_SPAN

    # Drawn the same way the trees draw a link in a description, and read off
    # the same scan the `o` key opens one with: what is underlined here is
    # exactly what standing on it will open
    for link in find_links(line):
        yield byte(link.start), byte(link.end), LINK

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
            # The two halves of the help window's section break: a faint rule,
            # and the title over it in the accent color.
            #
            # The title deliberately takes no background of its own. The cursor
            # is a block of `primary` with `background1` written into it, so a
            # title wearing those as a chip would swallow the cursor whole -
            # there would be nothing left for it to invert against, and typing
            # a header would happen somewhere the eye could not follow
            RULE_SPAN: Style(color=blend(theme.foreground1, theme.background2, 0.7)),
            HEADER: Style(color=theme.primary, bold=True),
            # The same underlined italic a link wears out on the todo rows,
            # so a URL looks like one thing wherever it is written
            LINK: Style(color=theme.primary, underline=True, italic=True),
        },
    )


class NoteEditor(TextArea):
    """
    A plain text editor that styles `**bold**`, `*italic*` and bullets as typed

    Two modes, the way the rest of dooit has two. The window opens in NORMAL,
    where the letters move the cursor about and nothing typed reaches the note,
    and `i` drops into INSERT, where they land in it. `escape` climbs back out
    one step at a time: INSERT to NORMAL, NORMAL to the todo the note is on.

    Selecting, copying and pasting work the same in either mode - shift with a
    motion picks text out, `ctrl+a` takes the lot, and `ctrl+c`/`ctrl+x`/`ctrl+v`
    do what they do in any other text field. Since the last two are edits, they
    take the note into INSERT rather than being refused there.
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
        # `ctrl+h` would be the mnemonic, but every terminal that does not
        # speak the kitty protocol sends it as a backspace; `t` for title is
        # the next letter along and is spent on nothing else here
        Binding("ctrl+t", "toggle_header", "Header", show=False),
        # Takes the key off TextArea, where it deletes the character to the
        # right of the cursor; here the whole note goes, after a y/N
        Binding("ctrl+d", "clear_note", "Clear the note", show=False),
        # What the key means in every other text field. TextArea spends it on
        # `cursor_line_start` instead, which `home` already covers
        Binding("ctrl+a", "select_all", "Select all", show=False),
    ]

    def __init__(self, text: str) -> None:
        # `tab_behavior` stays at its default of "focus", which is what lets
        # `escape` bubble up to the screen instead of being swallowed here.
        #
        # `read_only` is what NORMAL mode *is*: keystrokes still move the
        # cursor and pick text out, but none of them reach the document, so
        # the letters are free to mean motions instead of themselves
        super().__init__(text, read_only=True)

        # Raised by the first `g` of a `gg` and by nothing else
        self._pending_g = False

    @property
    def mode(self) -> str:
        return MODE_NORMAL if self.read_only else MODE_INSERT

    def enter_insert(self) -> None:
        if not self.read_only:
            return

        self.read_only = False
        self.note_screen.mode_changed()

    def enter_normal(self) -> None:
        if self.read_only:
            return

        self.read_only = True
        self.note_screen.mode_changed()

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

        lines = self.document.lines

        for row, line in enumerate(lines):
            following = lines[row + 1] if row + 1 < len(lines) else ""

            for start, end, name in scan_markup(line, following):
                highlights[row].append((start, end, name))

    def action_wrap(self, marker: str) -> None:
        """
        Put `marker` either side of the selection, or take it away again
        """

        # Marking text up is writing it: the note is being edited from here on
        self.enter_insert()

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

        self.enter_insert()

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
    def rule(self) -> str:
        """
        A rule as wide as it is allowed to be: `HEADER_WIDTH`, or the window
        when that is narrower, so the divider never wraps onto a second line
        """

        return RULE * max(3, min(HEADER_WIDTH, self.wrap_width or HEADER_WIDTH))

    def _delete_line(self, row: int) -> None:
        """
        Take a whole line out, along with the newline that ends it - or, for
        the last line of the note, the one that starts it, since there is no
        other way to leave the line count one shorter than it was
        """

        if row + 1 < self.document.line_count:
            start, end = (row, 0), (row + 1, 0)
        elif row:
            start, end = (row - 1, len(self.document[row - 1])), (row, len(self.document[row]))
        else:
            start, end = (row, 0), (row, len(self.document[row]))

        self.replace("", start, end, maintain_selection_offset=False)

    def _rule_row(self, row: int) -> Optional[int]:
        """
        Where the rule of the header `row` belongs to is, if there is one

        Standing on the rule counts as standing on the header it closes, so
        the key undoes a header from either of the two lines it is made of.
        """

        if RULE_RE.match(self.document[row]):
            return row

        below = row + 1

        if below < self.document.line_count and RULE_RE.match(self.document[below]):
            return below

        return None

    def action_toggle_header(self) -> None:
        """
        Close the current line off as a section title with a rule, or take the
        rule away again

        The header is the help window's section break: the title, and the rule
        drawn across underneath it. Only the rule is ever added or removed -
        the title is the line that was already there, and goes on being
        ordinary text that can be typed over, marked up and deleted.
        """

        self.enter_insert()

        row, column = self.cursor_location
        rule_row = self._rule_row(row)

        if rule_row is not None:
            self._delete_line(rule_row)

            # Standing on the rule, the title is the line above; standing on
            # the title, it is where it already was
            title = row - 1 if rule_row == row else row
            self.move_cursor((max(title, 0), column if title == row else 0))
            return

        line = self.document[row]
        self.insert("\n" + self.rule, (row, len(line)), maintain_selection_offset=False)
        self.move_cursor((row, column))

    def action_copy(self) -> None:
        """
        Copy what is picked out - or, when nothing is, the whole note

        Overrides the TextArea binding, which copies a selection and does
        nothing at all without one; a note is short enough that the whole of
        it is the obvious thing to mean by an unqualified copy.
        """

        copy_text(self.app, self.selected_text or self.text)

    def action_paste(self) -> None:
        """
        Drop the clipboard in at the cursor

        Overrides the TextArea binding, which pastes textual's own clipboard:
        that only ever holds what was copied inside dooit, and the point of
        the key here is to bring text in from somewhere else.

        A paste is an edit, so it takes the note into INSERT rather than being
        turned away in NORMAL: the keys after a paste are the ones that tidy
        up what was pasted.
        """

        text = paste_text(self.app)

        if not text:
            return

        self.enter_insert()

        if result := self._replace_via_keyboard(text, *self.selection):
            self.move_cursor(result.end_location)

    def action_cut(self) -> None:
        """
        Take the selection out and put it on the clipboard

        Overrides the TextArea binding for the same reason `copy` does - so
        the text goes out by both clipboard routes and not just textual's own
        - and, like `paste`, drops into INSERT instead of refusing in NORMAL.
        """

        start, _ = self.selection
        removed = self.selected_text or self.document[start[0]]

        self.enter_insert()
        super().action_cut()

        copy_text(self.app, removed)

    @property
    def note_screen(self) -> "NoteScreenBase":
        screen = self.screen

        assert isinstance(screen, NoteScreenBase)
        return screen

    def action_clear_note(self) -> None:
        """
        Offer to throw the whole note away; the screen puts the question
        """

        self.note_screen.request_clear()

    def _handle_normal_key(self, key: str) -> bool:
        """
        Act on a key pressed in NORMAL mode; True when it was one of ours

        Anything not answered here is handed on untouched, which is what keeps
        the shift-motions and the clipboard keys - all of them bindings - the
        same in both modes.
        """

        # Only the key straight after a `g` can be its second half, so the
        # flag is read and dropped in one go
        pending_g, self._pending_g = self._pending_g, False

        if key == "g":
            if pending_g:
                self.move_cursor((0, 0))
            else:
                self._pending_g = True

            return True

        if motion := NORMAL_MOTIONS.get(key):
            getattr(self, f"action_{motion}")()
            return True

        if key == "G":
            self.move_cursor(self.document.end)
            return True

        if key in INSERT_ENTRIES:
            self._enter_insert_at(key)
            return True

        if key == "o":
            self._open_link_under_cursor()
            return True

        if key == "O":
            self._open_line()
            return True

        return False

    def _open_link_under_cursor(self) -> None:
        """
        Open the link the cursor is standing on, and say so when there is none

        Nothing else: reading a note is not editing it, so the key that opens
        a link never lands the note in INSERT - not even by falling through to
        something that would.
        """

        row, column = self.cursor_location
        link = link_at(self.document[row], column)

        if link is None:
            self.note_screen.report("No link under the cursor")
            return

        self.note_screen.open_link(link.url)

    def _enter_insert_at(self, key: str) -> None:
        """
        vim's four ways in: at the cursor, past it, or at either end of the line
        """

        row, column = self.cursor_location
        line = self.document[row]

        if key == "a":
            self.move_cursor((row, min(column + 1, len(line))))

        elif key == "I":
            # Past the bullet rather than in front of it: on a bullet line the
            # text starts where the glyph ends
            bullet = BULLET_RE.match(line)
            self.move_cursor((row, bullet.end(1) if bullet else 0))

        elif key == "A":
            self.move_cursor((row, len(line)))

        self.enter_insert()

    def _open_line(self) -> None:
        """
        Start a line under this one and type on it

        On the shifted key, since the lowercase one is spent on opening links:
        the note is read far more often than a line is started in it, and a
        key that opens a link has to be a key that never writes anything.

        A line opened under a bullet gets a bullet of its own, the same way
        `enter` carries one on: this is how the next item of a list is written.
        """

        row, _ = self.cursor_location
        line = self.document[row]
        bullet = BULLET_RE.match(line)
        prefix = line[: bullet.end(1)] if bullet else ""

        self.enter_insert()

        self.move_cursor((row, len(line)))
        self.insert("\n" + prefix, maintain_selection_offset=False)

    async def _on_key(self, event: events.Key) -> None:
        """
        The keys of whichever mode the note is in, and the bullet that a new
        line carries over from the one above it
        """

        if self.note_screen.awaiting_clear:
            # The editor keeps the keyboard while the question stands, so the
            # answer arrives here rather than at a binding on the screen - and
            # is swallowed either way, so a `y` is an answer and not a letter
            event.stop()
            event.prevent_default()
            self.note_screen.answer_clear(event.key)
            return

        # The character rather than the key name, so that a keyboard where the
        # motions sit on `ö` is read the same way the trees read it
        key = self.note_screen.resolve_key(event)

        if self.read_only:
            if self._handle_normal_key(key):
                event.stop()
                event.prevent_default()

                # The cursor is the only thing a motion changes; a blink that
                # happened to be mid-off would hide the move that was just made
                self._restart_blink()

            # `escape` is left to bubble on purpose: with no mode left to drop
            # out of, what it drops out of is the window
            return

        if key == "escape":
            event.stop()
            event.prevent_default()
            self.enter_normal()
            return

        if event.key == "enter":
            row, column = self.cursor_location
            line = self.document[row]

            below = row + 1
            closed = (
                column == len(line)
                and below < self.document.line_count
                and RULE_RE.match(self.document[below])
            )

            if closed:
                # A title and its rule are one thing; `enter` from the end of
                # the title steps over the rule into the section it opens
                # rather than pushing the two of them apart
                event.stop()
                event.prevent_default()

                if below + 1 >= self.document.line_count:
                    self.insert(
                        "\n",
                        (below, len(self.document[below])),
                        maintain_selection_offset=False,
                    )

                self.move_cursor((below + 1, 0))
                return

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


class NoteScreenBase(BaseScreen):
    """
    A note in a window over the whole screen

    Everything about writing one lives here - the two modes, the debounce that
    writes it back, the y/N that throws it away - and the three things that
    differ between one note and another are left to whoever subclasses this:
    what the window is called, where the text is read from, and where it goes.
    """

    DEFAULT_CSS = """
    NoteScreenBase {
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

    # One line of hints per mode: the keys that do nothing where you are
    # standing would only be noise
    HINTS = {
        MODE_NORMAL: (
            "i insert    jklö move    o link    gg/G ends    "
            "ctrl+c copy    ctrl+d clear    esc close"
        ),
        # The formatting keys are what is worth advertising here; `ctrl+v` had
        # to go to make room for the header, and is the one key on the line
        # that every other text field in the world already taught
        MODE_INSERT: (
            "ctrl+b bold   ctrl+i italic   ctrl+l bullet   "
            "ctrl+t header   esc normal"
        ),
    }

    # Worded and escaped the way the confirm bar words a deletion elsewhere in
    # dooit, so the answer is the one the user already knows
    CLEAR_PROMPT = r"Clear the whole note? \[y/N]"

    def __init__(self) -> None:
        super().__init__()
        self._save_timer: Optional[Timer] = None
        self._report_timer: Optional[Timer] = None
        self._awaiting_clear = False

    @property
    def title_text(self) -> str:
        """
        What the window is called, written into its top border
        """

        raise NotImplementedError  # pragma: no cover

    def load_note(self) -> str:
        """
        The text the window opens on
        """

        raise NotImplementedError  # pragma: no cover

    def store_note(self, text: str) -> None:
        """
        Write the text back to wherever this note is kept

        Called on the debounce and again on the way out, so it is handed the
        same text more than once for every one time it changes: what to do
        about that belongs to whichever store is on the other end of it.
        """

        raise NotImplementedError  # pragma: no cover

    @property
    def editor(self) -> NoteEditor:
        return self.query_one(NoteEditor)

    @property
    def hint(self) -> Static:
        return self.query_one("#note-hint", Static)

    @property
    def awaiting_clear(self) -> bool:
        return self._awaiting_clear

    def compose(self) -> ComposeResult:
        editor = NoteEditor(self.load_note())
        editor.border_title = self.title_text

        yield editor
        yield Static(self.HINTS[MODE_NORMAL], id="note-hint")

    def on_mount(self) -> None:
        editor = self.editor
        editor.register_theme(build_theme(self.api.vars.theme))
        editor.theme = THEME_NAME

        # The window takes the keyboard, but in NORMAL mode: the note opens to
        # be read, and `i` is what says it is about to be written
        editor.focus()
        self.mode_changed()

    def mode_changed(self) -> None:
        """
        Redraw the two places the mode is written: the chip in the bottom
        border of the window, and the line of hints under it
        """

        mode = self.editor.mode

        self.editor.border_subtitle = f" {mode} "
        self.editor.set_class(mode == MODE_INSERT, "-insert")

        # A question standing in the hint line outranks the hints themselves;
        # answering it puts the right ones back
        if not self._awaiting_clear:
            self.hint.update(self.HINTS[mode])

    def report(self, message: str) -> None:
        """
        Say something in the hint line, and put the hints back afterwards

        The bar dooit talks through is on the screen underneath this one, so
        a note has to do its own talking - and the line the hints are written
        on is already there for it.
        """

        if self._report_timer is not None:
            self._report_timer.stop()

        self.hint.update(message)
        self._report_timer = self.set_timer(REPORT_TIMEOUT, self.mode_changed)

    def open_link(self, url: str) -> None:
        """
        Hand a URL to the browser, and say which one went

        Nothing about it shows up in here - the browser comes up somewhere
        else entirely, or nothing does - so the line underneath is what says
        the key landed.
        """

        if open_url(url):
            self.report(f"Opening {link_label(url)}")
        else:
            self.report("Found no browser to open the link with")

    @on(TextArea.Changed)
    def schedule_save(self, _: TextArea.Changed) -> None:
        if self._save_timer is not None:
            self._save_timer.stop()

        self._save_timer = self.set_timer(SAVE_DEBOUNCE, self.save)

    def save(self) -> None:
        self._save_timer = None
        self.store_note(self.editor.text)

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
        self.hint.remove_class("confirming")
        self.mode_changed()

        if key.lower() != "y":
            return

        self.editor.clear()

        # The debounce would get here on its own; writing it out now means the
        # row behind the window is right the moment the window closes
        self.save()

    def action_close(self) -> None:
        if self._save_timer is not None:
            self._save_timer.stop()

        # Nothing left to write the hints back onto once the window is gone
        if self._report_timer is not None:
            self._report_timer.stop()

        # Written out here as well as on the timer, so the last keystrokes
        # can't be lost inside the debounce window
        self.save()

        # `dismiss`, not `pop_screen`: popping throws the callback the screen
        # was pushed with away without running it, and that callback is what
        # redraws the row - so the note icon would not turn up until dooit was
        # restarted
        self.dismiss()


class NoteScreen(NoteScreenBase):
    """
    The note of one todo
    """

    def __init__(self, todo: Todo) -> None:
        super().__init__()
        self.todo = todo

    @property
    def title_text(self) -> str:
        """
        Whose note this is, so the window is not just a box of text
        """

        description = self.todo.description.strip() or "Note"

        if len(description) > TITLE_MAX:
            description = description[: TITLE_MAX - 1] + "…"

        return description

    def load_note(self) -> str:
        return self.todo.note or ""

    def store_note(self, text: str) -> None:
        if self.todo.note == text:
            return

        self.todo.note = text
        self.todo.save()
