import sys
from pathlib import Path
from platformdirs import user_cache_dir
from uuid import uuid4


def get_base_path() -> Path:
    """Get the base path for the application."""
    if path := getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS"):
        return Path(path) / "dooit"  # pragma: no cover

    return Path(__file__).parent.parent


DOOIT_CACHE_PATH = Path(user_cache_dir("dooit"))
BASE_PATH = get_base_path()


def generate_random_id():
    return uuid4().hex


class CssManager:
    base_css: Path = BASE_PATH / "ui" / "styles.tcss"

    def __init__(
        self,
        cache_path: Path = DOOIT_CACHE_PATH,
    ):
        self.cache_path: Path = cache_path
        self.stylesheets: Path = cache_path / "stylesheets"
        self.css_file: Path = cache_path / "dooit.tcss"
        self.theme: dict[str, str] | None = None

        cache_path.mkdir(parents=True, exist_ok=True)
        if not self.css_file.exists():
            self.write("")

        self.stylesheets.mkdir(
            parents=True,
            exist_ok=True,
        )

    def read_css(self) -> str:
        return self.css_file.read_text()

    def set_theme(self, theme: dict[str, str]):
        self.theme = theme

    def get_theme_css(self) -> str:
        if not self.theme:
            raise Exception("No theme set")

        css = ""
        for key, value in self.theme.items():
            css += f"${key}: {value};\n"
        return css

    def refresh_css(self):
        css = self.get_theme_css()
        with open(self.base_css, "r") as f:
            css = css + "\n" + f.read()

        self.stylesheets.mkdir(parents=True, exist_ok=True)
        for sheet in self.stylesheets.iterdir():
            with open(sheet, "r") as f:
                css = css + "\n" + f.read()

        self.write(css)

    def inject_css(self, css: str, _id: str | None = None) -> str:
        uuid = _id or generate_random_id()
        css_file = self.stylesheets / f"{uuid}.tcss"

        with open(css_file, "w") as f:
            f.write(css)

        self.refresh_css()
        return uuid

    def unject_css(self, _id: str) -> bool:
        css_file = self.stylesheets / f"{_id}.tcss"

        if not css_file.exists():
            return False

        css_file.unlink()
        self.refresh_css()
        return True

    def is_active(self, _id: str) -> bool:
        return (self.stylesheets / f"{_id}.tcss").exists()

    def write(self, css: str):
        with open(self.css_file, "w") as f:
            f.write(css)

    def cleanup(self):
        for sheet in self.stylesheets.iterdir():
            sheet.unlink()

        self.stylesheets.rmdir()
        self.refresh_css()
