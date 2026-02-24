# Dooit Theme

Dooit now supports a concept of themes which makes it much easier for all components of the config share a common color format
Here's the definition of the `Theme` class:

Each theme consists of these colors:


## Colors

#### Background Colors

- **`background1`**: The darkest background color.
- **`background2`**: A slightly lighter background color.
- **`background3`**: The lightest background color in the theme.

---

#### Foreground Colors

- **`foreground1`**: The darkest foreground color.
- **`foreground2`**: A slightly lighter foreground color.
- **`foreground3`**: The lightest foreground color in the theme.

---

#### Accent Colors

- **`primary`**: The primary accent color
- **`secondary`**: The secondary accent color
---

#### Other Colors

- **`red`** **`orange`** **`yellow`** **`green`** **`blue`** **`purple`** **`magenta`** **`cyan`**

## Usage

You can access the current colorscheme by using `theme` var from api.vars

```py
from dooit.ui.bridge import DooitAPI, subscribe
from dooit.ui.bridge.events import Startup

@subscribe(Startup)
def setup(api: DooitAPI, _):
    theme = api.vars.theme
    # red = theme.red
    # cyan = theme.cyan
    # so on ......
```

## How to change themes?

Import the theme you would like to set and then add it to the api

```py
from dooit.ui.bridge import DooitAPI, subscribe
from dooit.ui.bridge.events import Startup
from dooit_extras.themes import Gruvbox

@subscribe(Startup)
def layout_setup(api: DooitAPI, _):
    api.css.set_theme(Gruvbox)
```


## Creating your own colorscheme

If you want to create your own colorscheme, you can use the `DooitThemeBase` and overrride the colors

```py
from dooit.models.theme import DooitThemeBase


class Nord(DooitThemeBase):
    _name = "dooit-nord"

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
    blue: str = "#81a1c1"
    purple: str = "#B48EAD"
    magenta: str = "#B48EAD"
    cyan: str = "#8fbcbb"

    # accent colors
    primary: str = cyan
    secondary: str = blue
```
