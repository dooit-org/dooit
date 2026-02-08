from ._model_formatter_base import ModelFormatterBase


class TodoFormatter(ModelFormatterBase):
    def setup_formatters(self):
        self.description = self.get_formatter_store()
        self.due = self.get_formatter_store()
        self.effort = self.get_formatter_store()
        self.recurrence = self.get_formatter_store()
        self.urgency = self.get_formatter_store()
        self.status = self.get_formatter_store()


class WorkspaceFormatter(ModelFormatterBase):
    def setup_formatters(self):
        self.description = self.get_formatter_store()
