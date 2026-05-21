from ._model_formatter_base import ModelFormatterBase
from dooit.ui.widgets.trees import TodosTree, WorkspacesTree


class TodoFormatter(ModelFormatterBase):
    """
    Formatter for Todo model fields.

    Provides formatter stores for description, due, effort, recurrence,
    urgency, and status fields of todo items.
    """

    def setup_formatters(self):
        """Initialize formatter stores for each todo field."""
        self.description = self.get_formatter_store()
        self.due = self.get_formatter_store()
        self.effort = self.get_formatter_store()
        self.recurrence = self.get_formatter_store()
        self.urgency = self.get_formatter_store()
        self.status = self.get_formatter_store()

    def trigger(self) -> None:
        """Force a refresh on all TodosTree widgets in the current screen."""
        for widget in self.api.app.screen.query(TodosTree):
            widget.force_refresh()


class WorkspaceFormatter(ModelFormatterBase):
    """
    Formatter for Workspace model fields.

    Provides a formatter store for the description field of workspace items.
    """

    def setup_formatters(self):
        """Initialize formatter stores for each workspace field."""
        self.description = self.get_formatter_store()

    def trigger(self) -> None:
        """Force a refresh on all WorkspacesTree widgets in the current screen."""
        for widget in self.api.app.screen.query(WorkspacesTree):
            widget.force_refresh()
