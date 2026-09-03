from enum import Enum
from typing import List


class ProjectWidget(Enum):
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


ProjectLayout = List[ProjectWidget]
TodoLayout = List[TodoWidget]
