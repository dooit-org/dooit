from enum import Enum
from typing import List


class ProjectWidget(Enum):
    description = "description"
    tasks = "tasks"


class TodoWidget(Enum):
    description = "description"
    due = "due"
    scheduled = "scheduled"
    # When the todo was ticked off; only ever drawn by the Completed project
    completed = "completed"
    # When the todo was thrown away; only ever drawn by the Bin
    binned = "binned"
    priority = "priority"
    recurrence = "recurrence"
    status = "status"
    effort = "effort"
    note = "note"


ProjectLayout = List[ProjectWidget]
TodoLayout = List[TodoWidget]
