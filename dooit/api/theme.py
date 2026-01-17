from dataclasses import dataclass


@dataclass
class DooitThemeBase:
    background1: str = "#2E3440"  # Darkest
    background2: str = "#3B4252"  # Lighter
    background3: str = "#434C5E"  # Lightest

    # foreground colors
    foreground1: str = "#D8DEE9"  # Darkest
    foreground2: str = "#E5E9F0"  # Lighter
    foreground3: str = "#ECEFF4"  # Lightest

    # other colors
    red: str = "#BF616A"
    orange: str = "#D08770"
    yellow: str = "#EBCB8B"
    green: str = "#A3BE8C"
    blue: str = "#81A1C1"
    purple: str = "#B48EAD"
    magenta: str = "#B48EAD"
    cyan: str = "#8FBCBB"

    # accent colors
    primary: str = cyan
    secondary: str = blue

    @classmethod
    def to_css(cls) -> str:
        css = f"""\
$background1: {cls.background1};
$background2: {cls.background2};
$background3: {cls.background3};

$foreground1: {cls.foreground1};
$foreground2: {cls.foreground2};
$foreground3: {cls.foreground3};

$red: {cls.red};
$orange: {cls.orange};
$yellow: {cls.yellow};
$green: {cls.green};
$blue: {cls.blue};
$purple: {cls.purple};
$magenta: {cls.magenta};

$primary: {cls.primary};
$secondary: {cls.secondary};
"""

        return css
