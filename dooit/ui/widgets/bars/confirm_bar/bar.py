from typing import Callable
from rich.console import RenderableType

from dooit.ui.api.events import BarNotification
from .._base import BarBase

DEFFAULT_MSG = r"Are you sure? \[y/N]"


class ConfirmBar(BarBase):
    """
    A bar widget that prompts the user for yes/no confirmation.

    Displays a confirmation message and executes the callback
    only when the user confirms with 'y'.
    """

    DEFAULT_CSS = """
    ConfirmBar {
        padding-left: 1;
        padding-right: 1;
    }
    """

    def __init__(
        self,
        callback: Callable,
        message: str = DEFFAULT_MSG,
        *args,
        **kwargs,
    ):
        super().__init__(callback, *args, **kwargs)
        self.message = message

    def perform_action(self, cancel: bool):
        """Execute the confirmation callback if not cancelled."""
        if not cancel:
            self.callback()

    async def handle_keypress(self, key: str) -> None:
        """Handle a keypress, confirming on 'y' and cancelling on any other key."""
        cancel = key.lower() != "y"
        self.dismiss(cancel)
        if cancel:
            self.post_message(BarNotification("The items were retained", "info"))
        else:
            self.post_message(BarNotification("The items were deleted", "error"))

    def render(self) -> RenderableType:
        """Render the confirmation message."""
        return self.message
