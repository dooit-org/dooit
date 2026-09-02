import pyperclip
from typing import Optional, Union

from rich.text import Text


class Input:
    """
    A simple single line Text Input
    """

    _cursor: str = "|"
    highlight_pattern = ""
    is_editing = False

    # Inputs that only show a derived value refuse to be edited
    editable: bool = True

    def __init__(self, value="") -> None:
        self._value = value
        self._cursor_position = len(self._value)

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

    def render_editing(self, theme) -> Union[str, Text]:
        """
        What to draw while this field is being edited

        Formatters are bypassed during an edit, so a field that can say
        something useful about the half-typed buffer -- what a due date
        expression resolves to, say -- overrides this to add it.
        """

        return self.render()

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

    def stop_edit(self) -> None:
        self.is_editing = False

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
