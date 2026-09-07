from ._model_formatter_base import ModelFormatterBase
from dooit.ui.widgets.trees import TodosTree, ProjectsTree


class TodoFormatter(ModelFormatterBase):
    def setup_formatters(self):
        self.description = self.get_formatter_store()
        self.due = self.get_formatter_store()
        self.scheduled = self.get_formatter_store()
        self.completed = self.get_formatter_store()
        self.binned = self.get_formatter_store()
        self.effort = self.get_formatter_store()
        self.recurrence = self.get_formatter_store()
        self.priority = self.get_formatter_store()
        self.status = self.get_formatter_store()
        self.note = self.get_formatter_store()

    def trigger(self) -> None:
        for widget in self.api.app.screen.query(TodosTree):
            widget.force_refresh()


class ProjectFormatter(ModelFormatterBase):
    def setup_formatters(self):
        self.description = self.get_formatter_store()
        self.tasks = self.get_formatter_store()

    def trigger(self) -> None:
        for widget in self.api.app.screen.query(ProjectsTree):
            widget.force_refresh()
