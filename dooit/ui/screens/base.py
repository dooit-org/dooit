from typing import TYPE_CHECKING
from textual.app import events
from textual.screen import Screen

if TYPE_CHECKING:  # pragma: no cover
    from ..api import DooitAPI
    from ..tui import Dooit


class BaseScreen(Screen, inherit_bindings=False):
    """
    Base screen with function to resolve `Key` event to str
    """

    SPACE_CHARACTERS = (
        "\u0020\u00a0\u1680\u202f\u205f\u3000"
        "\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b"
    )

    @property
    def app(self) -> "Dooit":
        """Return the running Dooit application instance."""
        from ..tui import Dooit

        app = super().app
        assert isinstance(app, Dooit)

        return app

    @property
    def api(self) -> "DooitAPI":
        """Return the DooitAPI instance from the application."""
        return self.app.api

    def resolve_key(self, event: events.Key) -> str:
        """Resolve a Key event to a string representation of the pressed key."""
        if not event.character:
            return event.key

        if event.is_printable or event.character in self.SPACE_CHARACTERS:
            return event.character

        return event.key
