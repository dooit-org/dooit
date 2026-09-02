from enum import Enum
from typing import List


class WorkspaceWidget(Enum):
    description = "description"


class TodoWidget(Enum):
    description = "description"
    due = "due"
    priority = "priority"
    recurrence = "recurrence"
    status = "status"
    effort = "effort"


WorkspaceLayout = List[WorkspaceWidget]
TodoLayout = List[TodoWidget]
