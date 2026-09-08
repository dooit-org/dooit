"""
A whole task read out of one typed line, in the style of Todoist's quick add

The line is written the way the task would be said -- "call the dentist #Home
@phone p1 e1 tomorrow 09:00" -- and the markers below pick the fields out of
it: which project it is filed under, what it is tagged with, how urgent it is,
how big a job it is, and the day it is planned for. Everything none of them
claims is the description, so the sentence survives having been read.

A todo carries two dates, and a line saying one date means the day the work is
planned for: that is the one there is a day-to-day answer to, and the one the
Today and Upcoming panes are built on. The deadline is the other question, and
is asked by name -- `due=friday`, `due=3w` -- since a line rarely has cause to
say both.

Only the reading is done here. What the names mean -- which project `#Home`
is, whether there is one -- is the app's business, and is settled where the
database is.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from dooit.api.todo import MAX_EFFORT, MAX_PRIORITY

from .date_parser import looks_like_date_start, parse

# The project the task is filed under
PROJECT_MARKER = "#"

# A label is written into the description under dooit's own tag marker, which
# is what the row highlights and what `Todo.tags` reads back
TAG_MARKER = "@"

# A tag hung on the task. The same marker it is stored under, so a label is
# typed the way it will read back on the row.
LABEL_MARKER = TAG_MARKER

# What separates the steps of a project path, for the times a name alone is
# not enough to say which project is meant
PATH_SEPARATOR = "/"

# `#name` or `@name`, taken only where a word starts: an `@` in the middle of
# one is part of the word ("bob@example.com") rather than a marker. The quoted
# form is what lets a project name have a space in it.
MARKED = re.compile(r'(?:(?<=\s)|\A)([#@])(?:"([^"]+)"|(\S+))')

# The deadline, named because the bare date in a line is the other one. What
# follows the `=` is a date expression like any other, and can run past the
# word it starts in: `due=next monday at 16:00` is read whole.
DUE_MARKER = "due="
DUE = re.compile(rf"^{DUE_MARKER}(.*)$", re.IGNORECASE)

# `p2`, `e3`: the letter names the scale and the digit the step on it
SCALE = re.compile(r"^([pe])(\d+)$", re.IGNORECASE)

# The scales, by the letter they are typed under: what the field is called and
# how far it runs
SCALES = {
    "p": ("priority", MAX_PRIORITY),
    "e": ("effort", MAX_EFFORT),
}

# A label is one word, so that it can be written into the description as a tag
# and read back out of it again
LABEL = re.compile(r"^\w+$")

# The longest a date expression is looked for. "next monday at 16:00" is four
# words, and nothing in the grammar runs longer than that.
MAX_DATE_WORDS = 4

# Words that do nothing but tie a date to the text in front of it. They go
# along with the date, so that "call mum on friday" leaves "call mum" behind,
# and "move the call to wednesday" does not keep a dangling "to".
DATE_LEAD_WORDS = ("at", "on", "by", "to", "for")

# Words that join two halves of a sentence and are never part of a date. They
# have to be named because `dateutil` steps over them as noise: without this,
# "buy milk tomorrow and eggs" reads as tomorrow with the "and" taken along,
# and the eggs are left joined to the milk by nothing at all.
JOINING_WORDS = frozenset({"and", "then", "or"})

# Punctuation a date can be written up against in a sentence -- "tomorrow,
# then post it". Taken off before the words are read as a date, and gone
# along with them afterwards. The full stop is not among them: it is part of
# how a German date is written ("19.07.").
TRAILING_PUNCTUATION = ",;"


class QuickAddError(ValueError):
    """
    Something in the line was meant as a field and could not be read as one

    Carried up to the overlay as it is: the message is what gets shown, so it
    is written as the one line of warning it turns into.
    """


@dataclass
class QuickAddSpec:
    """
    What one line asked for, before anything has been looked up or written
    """

    description: str = ""
    # The project as it was typed, which may be a name or a path. Empty when
    # the line said nothing about it, and the task goes wherever the pane is.
    project: str = ""
    labels: List[str] = field(default_factory=list)
    priority: int = 0
    effort: int = 0
    scheduled: Optional[datetime] = None
    # The deadline, which is only ever there because the line asked for it by
    # name: a date said in passing is the day the work is planned for
    due: Optional[datetime] = None
    # The words the date was read out of, so the overlay can show what it took
    date_text: str = ""

    @property
    def described(self) -> str:
        """
        The description as it is stored: the text, with the tags after it

        A label is not a field of its own on a todo; it is a tag in the
        description, which is where dooit has always kept them and what the
        row already knows how to draw.
        """

        tags = [f"{TAG_MARKER}{label}" for label in self.labels]
        return " ".join([self.description, *tags]).strip()


def parse_quick_add(line: str, now: Optional[datetime] = None) -> QuickAddSpec:
    """
    Reads a line into the task it describes, or says why it cannot be read
    """

    spec = QuickAddSpec()
    rest = _take_marked(line, spec)

    # The named date first: it says where it begins, so it never has to be
    # guessed at, and taking it out leaves one date at most for the scan below
    words = _take_due(rest.split(), spec, now)
    words = _take_scales(words, spec)
    words = _take_date(words, spec, now)

    spec.description = " ".join(words).strip()

    if not spec.description:
        raise QuickAddError("Say what the task is")

    return spec


def _take_marked(line: str, spec: QuickAddSpec) -> str:
    """
    Pulls the `#project` and `@label` out, and hands back what is left
    """

    kept: List[str] = []
    end = 0

    for match in MARKED.finditer(line):
        marker, quoted, bare = match.groups()
        name = (quoted or bare).strip()

        # A doubled marker is a slip of the finger, not a project called `#x`
        if name.startswith((PROJECT_MARKER, LABEL_MARKER)):
            raise QuickAddError(f"Nothing named after {marker}")

        if marker == PROJECT_MARKER:
            if spec.project:
                raise QuickAddError("A task goes in one project")

            spec.project = name
        else:
            if not LABEL.match(name):
                raise QuickAddError(f"{LABEL_MARKER}{name} is not one word")

            if name not in spec.labels:
                spec.labels.append(name)

        kept.append(line[end : match.start()])
        end = match.end()

    kept.append(line[end:])

    rest = " ".join(kept)

    # A marker with nothing after it never matched above, and is a half typed
    # field rather than a word of the description
    for word in rest.split():
        if word in (PROJECT_MARKER, LABEL_MARKER):
            raise QuickAddError(f"Nothing named after {word}")

    return rest


def _take_due(
    words: List[str], spec: QuickAddSpec, now: Optional[datetime]
) -> List[str]:
    """
    Pulls the deadline out, and hands back what is left

    The expression starts inside the `due=` word and may run on past it, so
    the longest run of following words that resolves is taken: `due=next
    monday at 16:00` is one date and not a date followed by three words. It
    stops at anything that is plainly a field of its own -- `due=fri p1` is
    friday and a priority -- and at anything that will not resolve, which is
    what leaves `due=tom buy milk` with a task to do.

    Unlike the bare date in a line, a `due=` nobody can read is an error
    rather than a few words put back: it was asked for by name, so quietly
    filing it in the description would be losing it.
    """

    for index, word in enumerate(words):
        match = DUE.match(word)

        if not match:
            continue

        if spec.due is not None:
            raise QuickAddError("A task has one deadline")

        value = match.group(1)

        if not value.strip('"'):
            raise QuickAddError(f"Say a date after {DUE_MARKER}")

        rest = _due_expression(words, index, value, spec, now)

        if rest is None:
            raise QuickAddError(f"Could not read {DUE_MARKER}{value}")

        words = rest

        # The list has shifted under the loop; whatever is left is scanned
        # again from the start, which is also what catches a second `due=`
        return _take_due(words, spec, now)

    return words


def _due_expression(
    words: List[str],
    index: int,
    value: str,
    spec: QuickAddSpec,
    now: Optional[datetime],
) -> Optional[List[str]]:
    """
    Reads the deadline starting inside `words[index]`, longest run first
    """

    # How far the expression may run: to the end of what it could be, and
    # never across a word that is a field in its own right
    last = index + 1
    while (
        last < len(words)
        and last - index < MAX_DATE_WORDS
        and not SCALE.match(words[last])
        and not DUE.match(words[last])
        and not _joins(words[last])
    ):
        last += 1

    for end in range(last, index, -1):
        phrase = _phrase([value, *words[index + 1 : end]])
        date, understood = parse(phrase, now)

        if not understood or date is None:
            continue

        spec.due = date
        return words[:index] + words[end:]

    return None


def _take_scales(words: List[str], spec: QuickAddSpec) -> List[str]:
    """
    Pulls the `p1` and `e2` out, and hands back what is left
    """

    kept: List[str] = []

    for word in words:
        match = SCALE.match(word)

        if not match:
            kept.append(word)
            continue

        letter, digits = match.groups()
        name, highest = SCALES[letter.lower()]
        value = int(digits)

        if value > highest:
            raise QuickAddError(
                f"{name.capitalize()} runs {letter}0-{letter}{highest}"
            )

        setattr(spec, name, value)

    return kept


def _joins(word: str) -> bool:
    """
    Whether a word ties two halves of a sentence together rather than a date
    """

    return word.strip('"').rstrip(TRAILING_PUNCTUATION).lower() in JOINING_WORDS


def _phrase(words: Sequence[str]) -> str:
    """
    A run of words as the date expression they are being tried as
    """

    return " ".join(
        word.strip('"').rstrip(TRAILING_PUNCTUATION) for word in words
    )


def _take_date(
    words: List[str], spec: QuickAddSpec, now: Optional[datetime]
) -> List[str]:
    """
    Pulls the day the task is planned for out, and hands back what is left

    A line is written as what to do and then when to do it, so the scan works
    back from the end: the last date in it is the one that was meant, and
    anything earlier that merely looks like one is part of what the task is
    called. "friday standup notes tomorrow" is the friday standup notes,
    planned for tomorrow, and "march report next week" is the march report.

    At each ending it takes the longest run of words that resolves, so that
    "next monday at 16:00" is read whole rather than as the 16:00 it finishes
    on, and only spans opening on a word that could start a date are tried at
    all -- otherwise the 5 in "buy 5 apples" would be read as a day.

    The first date found this way is the only one: a task is planned for one
    day, and the rest of the line is what it is called.
    """

    for end in range(len(words), 0, -1):
        for start in range(max(0, end - MAX_DATE_WORDS), end):
            head = words[start].rstrip(TRAILING_PUNCTUATION)

            if not looks_like_date_start(head, alone=end - start == 1):
                continue

            if any(_joins(word) for word in words[start:end]):
                continue

            date, understood = parse(_phrase(words[start:end]), now)

            if not understood or date is None:
                continue

            # "on friday" is one thing said, not a word and then a date
            lead = start
            if lead and words[lead - 1].lower() in DATE_LEAD_WORDS:
                lead -= 1

            spec.scheduled = date
            spec.date_text = " ".join(words[lead:end])

            return words[:lead] + words[end:]

    return words


def split_path(name: str) -> Tuple[str, ...]:
    """
    A typed project name as the steps of a path down the tree
    """

    return tuple(step.strip() for step in name.split(PATH_SEPARATOR) if step.strip())
