from datetime import timedelta, datetime
from typing import Any, Callable, Literal, Optional, Union
from textual.message import Message

from dooit.api.model import DooitModel
from dooit.api import FixedProject, Project, Todo

# A pane can be showing a stored project or one of the fixed ones, and every
# event about "the current project" carries whichever it is
ProjectType = Union[Project, FixedProject]

ModeType = Literal["NORMAL", "INSERT", "DATE", "SORT", "CONFIRM"]
EmptyWidgetType = Literal["todo", "project", "no_search_results"]
PositionType = Literal["project", "todo"]
NotificationType = Literal["info", "warning", "error"]


# Super event


class DooitEvent(Message, bubble=True):
    """
    Base class for all events
    """


# Base events


class ProjectEvent(DooitEvent):
    """
    Base class for all project events
    """

    def __init__(self, project: ProjectType) -> None:
        super().__init__()
        self.project = project


class TodoEvent(DooitEvent):
    """
    Base class for all todo events
    """

    def __init__(self, todo: Todo) -> None:
        super().__init__()
        self.todo = todo


class ProjectChanged(ProjectEvent):
    """
    Base class for the events that leave a project different from how it was

    An event that only says where the cursor is stays out of here: this is what
    the panes listen to when they have to be redrawn, and redrawing on a mere
    selection would mean a rebuild per keystroke.
    """


class TodoChanged(TodoEvent):
    """
    Base class for the events that leave a todo different from how it was

    The same todo can be on screen in more than one pane at a time — the
    project it is filed under, and every fixed project that gathered it up — so
    what changes it has to reach further than the row it was changed in.
    """


# Events


class Startup(DooitEvent):
    """
    Emitted when the app starts
    """


class ShutDown(DooitEvent):
    """
    Emitted when user presses the exit app keybind
    """


class SwitchTab(DooitEvent):
    """
    Emitted when user needs to focus other pane
    """


class SpawnHelp(DooitEvent):
    """
    Emitted when user presses `?` in NORMAL mode
    """


class SpawnQuickAdd(DooitEvent):
    """
    Emitted when the user wants to type a whole task in one line
    """


class SpawnNote(DooitEvent):
    """
    Emitted when user wants to see and edit the note of a todo
    """

    def __init__(self, todo: Todo) -> None:
        super().__init__()
        self.todo = todo


class ModeChanged(DooitEvent):
    """
    Emitted when there is a change in the `status`
    """

    def __init__(self, mode: ModeType) -> None:
        super().__init__()
        self.mode: ModeType = mode


class SpawnSearch(DooitEvent):
    """
    Emitted when user wants to find a task anywhere in the tree
    """


class StartSort(DooitEvent):
    """
    Emitted when user wants to sort
    """

    def __init__(self, model: DooitModel, callback: Callable) -> None:
        super().__init__()
        self.model = model
        self.callback = callback


class GotoFixedProject(DooitEvent):
    """
    Emitted when user wants to jump straight into a fixed project

    The projects pane moves onto the project and the tasks pane takes over the
    focus, so that the todos can be walked through without another keystroke.
    """

    def __init__(self, key: str) -> None:
        super().__init__()
        self.key = key


class ShowConfirm(DooitEvent):
    """
    Emitted when confirmation from user is required

    The question can be spelled out by whatever is asking it: an edit that
    takes more than the row under the cursor with it has to say so, since the
    bar is the only place the size of it is ever mentioned. Leaving it out
    falls back to the plain "Are you sure?".
    """

    def __init__(self, callback: Callable, message: Optional[str] = None) -> None:
        super().__init__()
        self.callback = callback
        self.message = message


# Project events


class ProjectSelected(ProjectEvent):
    """
    Emitted when user selects a project
    """

    def __init__(self, project: ProjectType) -> None:
        super().__init__(project)


class ProjectRemoved(ProjectChanged):
    """
    Emitted when user removes a project
    """

    def __init__(self, project: Project) -> None:
        super().__init__(project)


class ProjectDescriptionChanged(ProjectChanged):
    """
    Emitted when user changes the description of a project
    """

    def __init__(self, old: str, new: str, project: Project) -> None:
        super().__init__(project)
        self.old = old
        self.new = new


# Todo events


class TodoSelected(TodoEvent):
    """
    Emitted when user selects a todo
    """

    def __init__(self, todo: Todo) -> None:
        super().__init__(todo)


class TodoRemoved(TodoChanged):
    """
    Emitted when user removes a todo
    """

    def __init__(self, todo: Todo) -> None:
        super().__init__(todo)


class TodoDescriptionChanged(TodoChanged):
    """
    Emitted when user changes the description of a todo
    """

    def __init__(self, old: str, new: str, todo: Todo) -> None:
        super().__init__(todo)
        self.old = old
        self.new = new


class TodoDueChanged(TodoChanged):
    """
    Emitted when user changes the due of a todo
    """

    def __init__(
        self, old: Optional[datetime], new: Optional[datetime], todo: Todo
    ) -> None:
        super().__init__(todo)
        self.new = new
        self.old = old


class TodoScheduledChanged(TodoChanged):
    """
    Emitted when user changes the scheduled date of a todo
    """

    def __init__(
        self, old: Optional[datetime], new: Optional[datetime], todo: Todo
    ) -> None:
        super().__init__(todo)
        self.new = new
        self.old = old


class TodoStatusChanged(TodoChanged):
    """
    Emitted when user changes the status of a todo
    """

    def __init__(self, old: str, new: str, todo: Todo) -> None:
        super().__init__(todo)
        self.old = old
        self.new = new


class TodoEffortChanged(TodoChanged):
    """
    Emitted when user changes the effort of a todo
    """

    def __init__(self, old: Optional[int], new: Optional[int], todo: Todo) -> None:
        super().__init__(todo)
        self.old = old
        self.new = new


class TodoRecurrenceChanged(TodoChanged):
    """
    Emitted when user changes the recurrence of a todo
    """

    def __init__(
        self, old: Optional[timedelta], new: Optional[timedelta], todo: Todo
    ) -> None:
        super().__init__(todo)
        self.old = old
        self.new = new


class TodoNoteChanged(TodoChanged):
    """
    Emitted when user changes the note of a todo
    """

    def __init__(self, old: str, new: str, todo: Todo) -> None:
        super().__init__(todo)
        self.old = old
        self.new = new


class TodoPriorityChanged(TodoChanged):
    """
    Emitted when user changes the priority of a todo
    """

    def __init__(self, old: int, new: int, todo: Todo) -> None:
        super().__init__(todo)
        self.old = old
        self.new = new


class BarNotification(DooitEvent):
    """
    Emitted when a notification is to be displayed
    """

    def __init__(
        self, message: str, level: NotificationType, auto_exit: bool = True
    ) -> None:
        super().__init__()
        self.message = message
        self.level: NotificationType = level
        self.auto_exit = auto_exit


class StartFieldEdit(DooitEvent):
    """
    Emitted when an edit is started on a column the pane does not draw

    There is nowhere in the row to put the buffer, so the bar takes it: the
    tree carries on with the edit, and the bar is only where it is drawn.
    """

    def __init__(self, tree: Any, column: str) -> None:
        super().__init__()
        self.tree = tree
        self.column = column


class QuitApp(DooitEvent):
    """
    Internally used Quit Event
    """
