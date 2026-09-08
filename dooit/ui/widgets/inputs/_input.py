from typing import Optional, Tuple

from rich.style import Style
from rich.text import Text

from dooit.utils.clipboard import copy_text, paste_text, running_app

# Keys that throw a selected value away rather than editing it: what was there
# is gone either way, so the delete itself has nothing left to act on.
# `ctrl+l` is not among them: it empties the whole buffer regardless, so it is
# left to fall through and do that instead of stopping at the selection
SELECTION_DELETE_KEYS = frozenset({"backspace", "delete", "ctrl+w", "ctrl+delete"})

# Keys that grow or shrink a selection instead of settling it: the anchor stays
# where it was, and the cursor moves out from under it exactly as far as the
# same key without shift would have moved it
SELECTION_EXTEND_KEYS = frozenset(
    {
        "shift+left",
        "shift+right",
        "ctrl+shift+left",
        "ctrl+shift+right",
        "shift+home",
        "shift+end",
    }
)


class Input:
    """
    A simple single line Text Input
    """

    _cursor: str = "|"
    highlight_pattern = ""
    is_editing = False

    # Where a selection was started from; the cursor is its other end, so the
    # two together are the selected span. `None` is no selection at all, and
    # an anchor sitting on the cursor is an empty one, which is the same thing
    _selection_anchor: Optional[int] = None

    # Inputs that only show a derived value refuse to be edited
    editable: bool = True

    def __init__(self, value="") -> None:
        self._value = value
        self._cursor_position = len(self._value)
        self._selection_anchor = None

    @property
    def value(self) -> str:
        return self._value

    @property
    def selection(self) -> Optional[Tuple[int, int]]:
        """
        The selected span as (start, end), or None when nothing is selected
        """

        if self._selection_anchor is None:
            return None

        start, end = sorted((self._selection_anchor, self._cursor_position))

        if start == end:
            return None

        return start, end

    @property
    def selected_text(self) -> str:
        span = self.selection

        if span is None:
            return ""

        return self._value[span[0] : span[1]]

    def draw(self) -> str:
        if self.is_editing:
            text = self._render_text_with_cursor()
        else:
            text = self.value

        return text

    def render(self) -> str:
        return self.draw().strip()

    def render_editing(self, theme) -> Text:
        """
        What to draw while this field is being edited

        Formatters are bypassed during an edit, so a field that can say
        something useful about the half-typed buffer -- what a due date
        expression resolves to, say -- overrides this to add it.

        Selected text is drawn as a highlighted block with no cursor in it,
        which is what says that typing replaces it instead of adding to it.
        The cursor sits at one end of the highlight either way, so the block
        already shows where the next keystroke lands.
        """

        # The buffer rather than `value`: a field that derives what it shows
        # from the model (an unset priority, say) still has the buffer the
        # keystrokes land in, and that is what is up for replacement
        span = self.selection

        if span is not None:
            text = Text(self._value)

            # spanned rather than styled as a whole, so that a subclass which
            # appends to this -- a due date's preview, say -- stays outside
            # the highlight instead of being drawn as part of the selection
            text.stylize(self.selection_style(theme), *span)
            return text

        return Text(self.render())

    @staticmethod
    def selection_style(theme) -> Style:
        """
        The inverted pill the bar already wears while a field is typed into
        """

        return Style(color=theme.background1, bgcolor=theme.secondary)

    def _render_text_with_cursor(self) -> str:
        """
        Produces renderable Text object combining value and cursor
        """

        return (
            self._value[: self._cursor_position]
            + self._cursor
            + self._value[self._cursor_position :]
        )

    def start_edit(self) -> None:
        self.is_editing = True

        # An edit that starts on a field which already holds something starts
        # with the whole of it selected, so that replacing it is just typing,
        # with no clearing out of the old value first
        self._cursor_position = len(self._value)
        self._selection_anchor = 0

    def stop_edit(self, cancel: bool = False) -> None:
        self.is_editing = False
        self._selection_anchor = None

    def _is_text_key(self, key: str) -> bool:
        """
        Whether this keypress puts something into the buffer
        """

        return (
            key in ("space", "tab", "ctrl+v")
            or key.startswith("events.Paste:")
            or len(key) == 1
        )

    def _settle_selection(self, key: str, span: Tuple[int, int]) -> None:
        """
        Spend the selection on the key that just arrived

        Anything that writes into the buffer, and anything that deletes out of
        it, takes the selected text with it. Everything else -- a cursor move,
        most of all -- only drops the selection and leaves the value alone.
        """

        if key in SELECTION_DELETE_KEYS or self._is_text_key(key):
            start, end = span
            self._value = self._value[:start] + self._value[end:]
            self._cursor_position = start

    def select_all(self) -> None:
        """
        Take the whole buffer into the selection
        """

        self._selection_anchor = 0
        self.move_cursor_to_end()

    def _extend_selection(self, key: str) -> None:
        """
        Move the cursor while leaving the anchor behind, growing the selection

        A first shift-move drops the anchor where the cursor stands, so the
        span starts out empty and is only what the move itself covers.
        """

        if self._selection_anchor is None:
            self._selection_anchor = self._cursor_position

        if key == "shift+left":
            self._move_cursor_backward()

        elif key == "shift+right":
            self._move_cursor_forward()

        elif key == "ctrl+shift+left":
            self._move_cursor_backward(word=True)

        elif key == "ctrl+shift+right":
            self._move_cursor_forward(word=True)

        elif key == "shift+home":
            self._cursor_position = 0

        elif key == "shift+end":
            self.move_cursor_to_end()

    def copy_selection(self) -> None:
        """
        Put the selection on the clipboard, or the whole field when there is
        none -- the way ctrl+c reads on a field nobody has selected in
        """

        text = self.selected_text or self._value

        if not text:
            return

        copy_text(running_app(), text)

    def paste_from_clipboard(self) -> None:
        """
        Drop what is on the clipboard in at the cursor

        This is one line, so a multi-line clipboard is squeezed onto one
        rather than being handed to a renderer that can only draw the first.
        """

        text = " ".join(paste_text(running_app()).splitlines())

        if text:
            self._insert_text(text)

    def _insert_text(self, text: Optional[str] = None) -> None:
        """
        Inserts text where the cursor is
        """

        if text is None:
            text = paste_text(running_app())

        self._value = (
            self._value[: self._cursor_position]
            + text
            + self._value[self._cursor_position :]
        )

        self._cursor_position += len(text)

    def _move_cursor_backward(self, word=False, delete=False) -> None:
        """
        Moves the cursor backwards..
        Optionally jumps over a word when pressed ctrl+left
        Optionally deletes the letter in case of backspace
        """

        prev = self._cursor_position

        if not word:
            self._cursor_position = max(self._cursor_position - 1, 0)
        else:
            while self._cursor_position:
                if self._value[self._cursor_position - 1] != " " and (
                    self._cursor_position == 1
                    or self._value[self._cursor_position - 2] == " "
                ):
                    self._cursor_position -= 1
                    break

                self._cursor_position -= 1

        if delete:
            self._value = self._value[: self._cursor_position] + self._value[prev:]

    def _move_cursor_forward(self, word=False, delete=False) -> None:
        """
        Moves the cursor forward..
        Optionally jumps over a word when pressed ctrl+right
        Optionally deletes the letter in case of del or ctrl+del
        """

        prev = self._cursor_position

        if not word:
            self._cursor_position = min(self._cursor_position + 1, len(self._value))
        else:
            while self._cursor_position < len(self._value):
                if (
                    self._cursor_position != prev
                    and self._value[self._cursor_position - 1] == " "
                    and (
                        self._cursor_position == len(self._value) - 1
                        or self._value[self._cursor_position] != " "
                    )
                ):
                    break

                self._cursor_position += 1

        if delete:
            self._value = self._value[:prev] + self._value[self._cursor_position :]
            self._cursor_position = prev  # Because the cursor never actually moved :)

    def clear_input(self) -> None:
        self.move_cursor_to_end()
        while self._value:
            self.keypress("backspace")

    def move_cursor_to_end(self) -> None:
        self._cursor_position = len(self._value)

    def keypress(self, key: str) -> None:
        # Selecting, which is the one thing that leaves an existing selection
        # standing: these keys are what builds it up in the first place
        if key in SELECTION_EXTEND_KEYS:
            self._extend_selection(key)
            return

        if key == "ctrl+a":
            self.select_all()
            return

        # A copy leaves the selection where it is: what was just copied is
        # usually about to be replaced, or moved away from
        if key == "ctrl+c":
            self.copy_selection()
            return

        span = self.selection
        self._selection_anchor = None

        if span is not None:
            self._settle_selection(key, span)

            # The selected text is already gone; a delete on top of that
            # would eat into what is left either side of it
            if key in SELECTION_DELETE_KEYS:
                return

        # Moving backward
        if key == "left":
            self._move_cursor_backward()

        elif key == "ctrl+left":
            self._move_cursor_backward(word=True)

        elif key == "backspace":  # Backspace
            self._move_cursor_backward(delete=True)

        elif key == "ctrl+w":
            self._move_cursor_backward(word=True, delete=True)

        # Moving forward
        elif key == "right":
            self._move_cursor_forward()

        elif key == "ctrl+right":
            self._move_cursor_forward(word=True)

        elif key == "delete":
            self._move_cursor_forward(delete=True)

        elif key == "ctrl+delete":
            self._move_cursor_forward(word=True, delete=True)

        # clear all input
        elif key == "ctrl+l":
            self.clear_input()

        # EXTRAS
        elif key == "home":
            self._cursor_position = 0

        elif key == "end":
            self.move_cursor_to_end()

        elif key == "tab":
            self._insert_text("\t")

        elif key == "space":
            self._insert_text(" ")

        elif key == "ctrl+v":
            self.paste_from_clipboard()

        elif key.startswith("events.Paste:"):
            self._insert_text(key[13:])

        elif len(key) == 1:
            self._insert_text(key)
