from pathlib import Path
from tempfile import TemporaryDirectory

from dooit.models.theme import DooitThemeBase
from dooit.utils import CssManager


class TestTheme(DooitThemeBase):
    _name = "test_theme"


# ----------------------------------------

RANDOM_CSS = """
#random_css {
    background: red;
}
"""


def test_css_injections():
    cache_path = Path(TemporaryDirectory().name)
    manager = CssManager(cache_path=cache_path)

    injection_id = manager.inject_css(RANDOM_CSS)
    assert RANDOM_CSS in manager.read_css()

    assert manager.is_active(injection_id)

    assert manager.unject_css(injection_id)
    assert RANDOM_CSS not in manager.read_css()

    incorrect_id = "incorrect_id"
    assert not manager.unject_css(incorrect_id)
