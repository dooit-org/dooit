class DooitThemeBase:
    _name: str = "dooit-base"

    # background colors
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


class TokyoNight(DooitThemeBase):
    """
    The "night" variant of Tokyo Night: a deep blue-black ground, text in a
    washed periwinkle, and a palette that leans blue/purple, with the warm
    colors held back for the things that carry a meaning (due dates, priority).

    The three backgrounds are the ground itself, the raised bar, and the step
    above it that borders and the highlighted row are drawn in; the three
    foregrounds run from the gray that dim text fades towards up to the color
    the rows themselves are written in.
    """

    _name = "tokyo-night"

    # background colors
    background1: str = "#1A1B26"  # Darkest
    background2: str = "#1F2335"  # Lighter
    background3: str = "#2F334D"  # Lightest

    # foreground colors
    foreground1: str = "#A9B1D6"  # Darkest
    foreground2: str = "#C0CAF5"  # Lighter
    foreground3: str = "#D0D7F7"  # Lightest

    # other colors
    red: str = "#F7768E"
    orange: str = "#FF9E64"
    yellow: str = "#E0AF68"
    green: str = "#9ECE6A"
    blue: str = "#7AA2F7"
    purple: str = "#9D7CD8"
    magenta: str = "#BB9AF7"
    cyan: str = "#7DCFFF"

    # accent colors
    primary: str = blue
    secondary: str = magenta
