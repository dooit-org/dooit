from sqlalchemy.orm import Mapped, mapped_column

from .manager import manager
from .model import BaseModel, BaseModelMixin


# The pinned note is one note for the whole of dooit rather than one per todo,
# so the table it lives in holds exactly one row, and this is its id. Fixing it
# is what makes "the pinned note" something that can be fetched rather than
# searched for, and what stops a second one from ever being written.
PINNED_NOTE_ID = 1


class PinnedNote(BaseModel, BaseModelMixin):
    """
    The scratchpad: a note that belongs to nothing in particular

    It is kept in the database beside the todos rather than in a file of its
    own, so that it travels with them: what is jotted down before it is a task
    is as much the user's work as the tasks are, and a note left behind by a
    copied database would go missing exactly when it mattered.

    The table is created by `metadata.create_all` on the way in like every
    other one, so a database that predates the note grows it on first launch
    with nothing to migrate - there is no old column to carry over.
    """

    id: Mapped[int] = mapped_column(primary_key=True, default=PINNED_NOTE_ID)
    note: Mapped[str] = mapped_column(default="")

    @classmethod
    def instance(cls) -> "PinnedNote":
        """
        The one row, written the first time anybody asks for it
        """

        row = manager.session.get(cls, PINNED_NOTE_ID)

        if row is None:
            row = cls(id=PINNED_NOTE_ID, note="")
            manager.save(row)

        return row

    @classmethod
    def get_text(cls) -> str:
        return cls.instance().note or ""

    @classmethod
    def set_text(cls, text: str) -> None:
        """
        Write the note back, and only when there is something to write

        The editor saves on a debounce and again on the way out, so the same
        text arrives here more than once for every one time it changes; a
        commit per keystroke would leave the trees refreshing themselves off
        the database poller for as long as the note was being typed in.
        """

        row = cls.instance()

        if row.note == text:
            return

        row.note = text
        manager.save(row)
