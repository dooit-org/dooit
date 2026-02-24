from .formatter_store import FormatterStore


class ModelFormatterBase:
    def __init__(self) -> None:
        self.setup_formatters()

    def get_formatter_store(self) -> FormatterStore:
        return FormatterStore()

    def setup_formatters(self) -> None:  # pragma: no cover
        pass
