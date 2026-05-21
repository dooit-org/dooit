from ..inputs.model_inputs import (
    Due,
    Effort,
    Recurrence,
    Status,
    TodoDescription,
    Urgency,
)
from .base_renderer import BaseRenderer, Todo


class TodoRender(BaseRenderer[Todo]):
    """
    Renderer for Todo model items.

    Manages the input components for all editable Todo attributes
    including description, due date, status, urgency, effort, and recurrence.
    """

    @property
    def model(self) -> Todo:
        """Return the underlying Todo model."""
        return self._model

    def post_init(self):
        """Initialize input components for each editable Todo attribute."""
        self.description = TodoDescription(self.model)
        self.due = Due(self.model)
        self.status = Status(self.model)
        self.urgency = Urgency(self.model)
        self.effort = Effort(self.model)
        self.recurrence = Recurrence(self.model)
