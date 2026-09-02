from enum import Enum
from typing import List


class WorkspaceWidget(Enum):
    description = "description"
    tasks = "tasks"


class TodoWidget(Enum):
    description = "description"
    due = "due"
    scheduled = "scheduled"
    priority = "priority"
    recurrence = "recurrence"
    status = "status"
    effort = "effort"
    note = "note"


WorkspaceLayout = List[WorkspaceWidget]
TodoLayout = List[TodoWidget]
