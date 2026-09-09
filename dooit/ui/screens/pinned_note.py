from dooit.api import PinnedNote

from .note import NoteScreenBase


# What the window is called. Not the description of anything, the way a todo's
# note window is titled: this note is the one that belongs to nothing
PINNED_TITLE = "Pinned Note"


class PinnedNoteScreen(NoteScreenBase):
    """
    The scratchpad: one note for the whole of dooit, in the note window

    The same editor a todo's note is written in, pointed at the note that
    belongs to nothing: what is jotted down here needs no task to hang off,
    which is the whole point of it - a thought is worth keeping before it is
    worth filing.
    """

    @property
    def title_text(self) -> str:
        return PINNED_TITLE

    def load_note(self) -> str:
        return PinnedNote.get_text()

    def store_note(self, text: str) -> None:
        PinnedNote.set_text(text)
