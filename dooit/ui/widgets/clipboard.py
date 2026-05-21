from dooit.api.model import DooitModel
from dooit.ui.widgets.todo import TodoWidget


class Clipboard:
    """
    Clipboard to copy models (Todos and Workspaces) as a whole
    """

    data = None

    def copy(self, widget: TodoWidget):
        """Copy the model data from the given todo widget to the clipboard."""
        model: DooitModel = widget.model
        self.data = model.commit()

    @property
    def has_data(self) -> bool:
        """Return whether the clipboard currently holds any data."""
        return bool(self.data)
