import pyperclip
from typing import Optional

from rich.style import Style
from rich.text import Text

# Keys that throw a selected value away rather than editing it: what was there
# is gone either way, so the delete itself has nothing left to act on
SELECTION_DELETE_KEYS = frozenset(
    {"backspace", "delete", "ctrl+w", "ctrl+delete", "ctrl+l"}
)


class Input:
    """
    A simple single line Text Input
    """

    _cursor: str = "|"
    highlight_pattern = ""
    is_editing = False

    # Whether the whole value is selected, the way an edit starts on a field
    # that already holds something: the next thing typed replaces it
    _selecting: bool = False

    # Inputs that only show a derived value refuse to be edited
    editable: bool = True

    def __init__(self, value="") -> None:
        self._value = value
        self._cursor_position = len(self._value)
        self._selecting = False

    @property
    def value(self) -> str:
        return self._value

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

        A value that is still selected is drawn as one highlighted block
        rather than as a buffer with a cursor sitting in it, which is what
        says that typing replaces it instead of adding to it.
        """

        # The buffer rather than `value`: a field that derives what it shows
        # from the model (an unset priority, say) still has the buffer the
        # keystrokes land in, and that is what is up for replacement
        if self._selecting:
            text = Text(self._value)

            # spanned rather than styled as a whole, so that a subclass which
            # appends to this -- a due date's preview, say -- stays outside
            # the highlight instead of being drawn as part of the selection
            text.stylize(self.selection_style(theme), 0, len(self._value))
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
        # with it selected, so that replacing it is just typing, with no
        # clearing out of the old value first
        self._selecting = bool(self._value)

    def stop_edit(self, cancel: bool = False) -> None:
        self.is_editing = False
        self._selecting = False

    def _is_text_key(self, key: str) -> bool:
        """
        Whether this keypress puts something into the buffer
        """

        return (
            key in ("space", "tab") or key.startswith("events.Paste:") or len(key) == 1
        )

    def _settle_selection(self, key: str) -> None:
        """
        Drop the whole-value selection against the key that just arrived

        Anything that writes into the buffer, and anything that deletes out of
        it, takes the selected value with it. Everything else -- a cursor move,
        most of all -- only drops the selection and leaves the value alone.
        """

        self._selecting = False

        if key in SELECTION_DELETE_KEYS or self._is_text_key(key):
            self._value = ""
            self._cursor_position = 0

    def _insert_text(self, text: Optional[str] = None) -> None:
        """
        Inserts text where the cursor is
        """

        # Will throw an error if `xclip` if not installed on the linux(Xorg) system,
        # should work just fine on windows and mac

        if text is None:
            text = str(pyperclip.paste())

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
        if self._selecting:
            self._settle_selection(key)

            # The selected value is already gone; a delete on top of that
            # would eat into whatever it gets replaced with
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

        elif key.startswith("events.Paste:"):
            self._insert_text(key[13:])

        elif len(key) == 1:
            self._insert_text(key)
