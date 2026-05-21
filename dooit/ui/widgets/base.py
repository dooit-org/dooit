from textual.widget import Widget
from dooit.ui.api.events import ModeChanged, ModeType


class HelperWidget(Widget):
    """
    Helper Widgets to Tree Widgets
    Currently base for `SortOptions` and `SearchMenu`
    """

    DEFAULT_CSS = """
    HelperWidget {
        layer: L1;
        display: none;
    }
    """

    _status: ModeType

    async def hide(self) -> None:
        """Hide the widget and switch back to NORMAL mode."""
        self.styles.layer = "L1"
        self.display = False
        self.post_message(ModeChanged("NORMAL"))

    async def start(self) -> None:
        """Show the widget and activate its associated mode."""
        self.styles.layer = "L4"
        self.display = True
        self.post_message(ModeChanged(self._status))

    async def cancel(self) -> None:
        """Cancel the current operation and hide the widget."""
        await self.hide()

    async def stop(self):
        """Stop the widget and finalize the current operation."""
        pass
