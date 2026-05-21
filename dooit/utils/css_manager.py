import sys
from pathlib import Path
from typing import Optional, Type, Union
from platformdirs import user_cache_dir
from dooit.api.theme import DooitThemeBase
from uuid import uuid4

dooit_cache_path = Path(user_cache_dir("dooit"))

if getattr(sys, "frozen", False):
    BASE_PATH = Path(sys._MEIPASS) / "dooit"  # pragma: no cover (binary pkg)
else:
    BASE_PATH = Path(__file__).parent.parent


def generate_random_id():
    """Generate a random hex string identifier using UUID4."""
    return uuid4().hex


class CssManager:
    """
    Manages CSS stylesheet generation, theme application, and injection for the dooit UI.
    """

    base_css: Path = BASE_PATH / "ui" / "styles.tcss"
    themes = dict()

    def __init__(
        self,
        theme: DooitThemeBase = DooitThemeBase(),
        cache_path: Path = dooit_cache_path,
    ):
        self.theme: DooitThemeBase = theme
        self.cache_path = cache_path
        self.stylesheets: Path = cache_path / "stylesheets"
        self.css_file: Path = cache_path / "dooit.tcss"

        cache_path.mkdir(parents=True, exist_ok=True)
        if not self.css_file.exists():
            self.write("")

        self.stylesheets.mkdir(
            parents=True,
            exist_ok=True,
        )

    def read_css(self) -> str:
        """Read and return the current compiled CSS content."""
        return self.css_file.read_text()

    def refresh_css(self):
        """Regenerate the combined CSS from the theme, base styles, and injected stylesheets."""
        css = self.theme.to_css()

        # setup base variables
        with open(self.base_css, "r") as f:
            css = css + "\n" + f.read()

        # inject extra stylesheets
        self.stylesheets.mkdir(parents=True, exist_ok=True)
        for sheet in self.stylesheets.iterdir():
            with open(sheet, "r") as f:
                css = css + "\n" + f.read()

        self.write(css)

    def add_theme(self, theme: Type[DooitThemeBase]):
        """Register a theme class so it can be activated later by name."""
        self.themes[theme._name] = theme()
        self.refresh_css()

    def set_theme(self, theme: Union[str, Type[DooitThemeBase]]):
        """Set the active theme by name or class and refresh the CSS."""
        if isinstance(theme, str):
            self.theme = self.themes.get(theme, DooitThemeBase)
        else:
            self.theme = theme()

        self.refresh_css()

    def inject_css(self, css: str, _id: Optional[str] = None) -> str:
        """Inject custom CSS as a stylesheet file and return its identifier."""
        uuid = _id or generate_random_id()
        css_file = self.stylesheets / f"{uuid}.tcss"

        with open(css_file, "w") as f:
            f.write(css)

        self.refresh_css()
        return uuid

    def unject_css(self, _id: str) -> bool:
        """Remove a previously injected stylesheet by its identifier."""
        css_file = self.stylesheets / f"{_id}.tcss"

        if not css_file.exists():
            return False

        css_file.unlink()
        self.refresh_css()
        return True

    def is_active(self, _id: str) -> bool:
        """Check whether a stylesheet with the given identifier is currently active."""
        return (self.stylesheets / f"{_id}.tcss").exists()

    def write(self, css: str):
        """Write CSS content to the compiled stylesheet file."""
        with open(self.css_file, "w") as f:
            f.write(css)

    def cleanup(self):
        """Remove all injected stylesheets and refresh the CSS."""
        for sheet in self.stylesheets.iterdir():
            sheet.unlink()

        self.stylesheets.rmdir()
        self.refresh_css()
