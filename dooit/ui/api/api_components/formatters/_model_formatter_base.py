from typing import TYPE_CHECKING

from .formatter_store import FormatterStore

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


class ModelFormatterBase:
    def __init__(self, api: "DooitAPI") -> None:
        self.api = api
        self.setup_formatters()

    def get_formatter_store(self) -> FormatterStore:
        return FormatterStore(self.api)

    def setup_formatters(self) -> None:  # pragma: no cover
        pass
