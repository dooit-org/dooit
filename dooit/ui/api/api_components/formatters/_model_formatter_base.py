from typing import TYPE_CHECKING

from .formatter_store import FormatterStore

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


class ModelFormatterBase:
    """
    Base class for model-specific formatters.

    Provides the scaffolding for creating and managing formatter stores
    that control how model fields are rendered in the UI.
    """

    def __init__(self, api: "DooitAPI") -> None:
        self.api = api
        self.setup_formatters()

    def get_formatter_store(self) -> FormatterStore:
        """Create and return a new FormatterStore bound to this model formatter's trigger."""
        return FormatterStore(self.trigger, self.api)

    def setup_formatters(self) -> None:  # pragma: no cover
        """Initialize formatter stores for each field. Override in subclasses."""
        pass

    def trigger(self) -> None:  # pragma: no cover
        """Trigger a UI refresh for the associated widget tree. Override in subclasses."""
        pass
