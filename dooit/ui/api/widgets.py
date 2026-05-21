from enum import Enum
from typing import List


class WorkspaceWidget(Enum):
    """
    Enum of available widget columns for workspace rows in the layout.
    """

    description = "description"


class TodoWidget(Enum):
    """
    Enum of available widget columns for todo rows in the layout.
    """

    description = "description"
    due = "due"
    urgency = "urgency"
    recurrence = "recurrence"
    status = "status"
    effort = "effort"


WorkspaceLayout = List[WorkspaceWidget]
TodoLayout = List[TodoWidget]
