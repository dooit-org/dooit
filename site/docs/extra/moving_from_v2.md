# Moving from Dooit V2 to V3

First of all, thanks you so much if you've been using dooit already. Really means a lot to me!

## How to migrate?

Since I've rewrote the app from scratch, every single thing is pretty much changed but in a good way. \
You still have _almost everything_ (dont worry, the replacements are sane) from v2 + extra on top of that :star:

There are two steps to migrate from v2:

### Migrating Data

Run this in the terminal and it should be taken care of: \
You'll also be prompted for this if not already done

```bash
dooit migrate
```

### Migrating Config

This requires a bit more work but completly an easy process.

Below, I'll split parts of it and provide you with newer format

***Let's start***


## Colors

:::tip :bulb: TIP
Check out [`Theme`](../configuration/theme.md) for more info
:::

### Old

```py
dark_black = "#252a34"
black = "#2e3440"
white = "#e5e9f0"
grey = "#d8dee9"
red = "#bf616a"
frost_green = "#8fbcbb"
cyan = "#88c0d0"
green = "#a3be8c"
yellow = "#ebcb8b"
blue = "#81a1c1"
magenta = "#b48ead"
orange = "#d08770"
```

### New

Dooit now has a dedicated theme api for colors so that the colors will match properly with everything


```py
from dooit.ui.api import DooitAPI, subscribe
from dooit.ui.api.events import Startup

@subscribe(Startup)
def foo(api: DooitAPI, _):
    theme = api.vars.theme
```

## Dashboard

:::tip :bulb: TIP
Check out [`Dashboard`](../configuration/dashboard.md) for more info
:::

:::info :grey_exclamation: NOTE
I have removed the ascii dashboard section from old config since it takes too much lines of code
For that please check out [`Dashboard`](../configuration/dashboard.md) section and [`Sample configs from Dooit Extras`](https://dooit-org.github.io/dooit-extras/configs/nord.html)
:::

Dashboard hasn't changed much, just that you call a different function to set it + now you have better color support

### Old

```py
ART = "some ascii art"
NL = " \n"
SEP = colored("─" * 60, "d " + grey) # some function to color
help_message = f"Press {colored('?', magenta)} to spawn help menu"
DASHBOARD = [ART, NL, SEP, NL, NL, NL, help_message]
```

### New

```py
from dooit.ui.api import DooitAPI, subscribe
from dooit.ui.api.events import Startup
from rich.text import Text


@subscribe(Startup)
def dashboard_setup(api: DooitAPI, _):

    def colored(text, color):
        return Text(text, style = color).markup

    theme = api.vars.theme

    ART = "some ascii art"
    NL = " \n"
    SEP = Text("─" * 60, "d " + theme.background3)
    help_message = f"Press {colored('?', magenta)} to spawn help menu"
    DASHBOARD = [ART, NL, SEP, NL, NL, NL, help_message]

    api.dashboard.set(DASHBOARD)
```


## Bar

:::tip :bulb: TIP
Check out [`Bar`](../configuration/bar.md) for more info
:::

:::info :grey_exclamation: NOTE
The function `get_message` is now of no use hence removed. \
Dooit will now flash any kind of messages covering the whole bar
:::

### Old

```py
def get_status(status):
    return colored(f" {status} ", "r " + blue)


def get_message(message):
    return " " + message


def get_clock() -> Text:
    return Text(f"{datetime.now().time().strftime(' %X ')}", "r " + cyan)


def get_username():
    try:
        username = os.getlogin()
    except OSError:
        uid = os.getuid()
        import pwd

        username = pwd.getpwuid(uid).pw_name
    return Text(f" {username} ", "r " + blue)

bar = {
    "A": [(get_status, 0.1)],
    "C": [(get_clock, 1), (get_username)],
}
```

### New

Most of the common widgets that you might wanna have should already be in [`dooit-extras`](https://dooit-org.github.io/dooit-extras/widgets/clock.html)
If you still want to have custom functions, check out [`Custom`](https://dooit-org.github.io/dooit-extras/widgets/custom.html) widget and use the above functions like that

```py
from dooit_extras.bar_widgets import Mode, Spacer, Clock, Date
from dooit.ui.api.events import Startup
from dooit.ui.api import DooitAPI, subscribe


@subscribe(Startup)
def setup(api: DooitAPI, _):
    theme = api.vars.theme
    api.bar.set( 
        [
            Mode(api),
            Spacer(api, width = 0),
            Clock(api, fmt=" 󰥔 {} ", bg=theme.yellow),
            Spacer(api, width = 1),
            Date(api, fmt = " {} ")
        ]
    )
```

## Layout

:::tip :bulb: TIP
Check out [`Layouts`](../configuration/layout.md) for more info
:::

Dooit now provides a layout api to order your columns

### Old

```py
COLUMN_ORDER = ["description", "due", "urgency"]  # order of columns
```

### New

```py
from dooit.ui.api.widgets import TodoWidget, ProjectWidget

@subscribe(Startup)
def layout_setup(api: DooitAPI, _):
    api.layouts.project_layout = [ProjectWidget.description]

    api.layouts.todo_layout = [
        TodoWidget.status,
        TodoWidget.description, 
        TodoWidget.recurrence,
        TodoWidget.due,
        TodoWidget.urgency,
    ]
```

## Formatting

:::tip :bulb: TIP
Check out [`Formatters`](../configuration/formatter.md) for more info
:::

Formatting for projects and todos is now even more customizable! \
You can use dooit formatters to custom format your items :D

Plus, some general settings from the old config as well

### Old

```py
#################################
#           WORKSPACE           #
#################################
WORKSPACE = {
    "editing": cyan,
    "pointer": ">",
    "children_hint": "+",  # "[{count}]", # vars: count
    "start_expanded": False,
}

COLUMN_ORDER = ["description", "due", "urgency"]  # order of columns
TODO = {
    "color_todos": False,
    "editing": cyan,
    "pointer": ">",
    "children_hint": colored(
        " ({done}/{total})", green
    ),  # vars: remaining, done, total
    # "children_hint": "[b magenta]({remaining}!)[/b magenta]",
    "due_icon": "? ",
    "effort_icon": "+",
    "effort_color": yellow,
    "recurrence_icon": "!",
    "recurrence_color": blue,
    "tags_color": red,
    "completed_icon": "x",
    "pending_icon": "o",
    "overdue_icon": "!",
    "urgency1_icon": "A",
    "urgency2_icon": "B",
    "urgency3_icon": "C",
    "urgency4_icon": "D",
    "start_expanded": False,
    "initial_urgency": 1,
    "urgency1_color": "green",
    "urgency2_color": "yellow",
    "urgency3_color": "orange",
    "urgency4_color": "red",
}

```

## Keybindings

:::tip :bulb: TIP
Check out [`Keys`](../configuration/keys.md) for more info
:::

Keybidings now are much more easier to understand and implement + now you get support for custom keybindings executing some custom code

You can get a full list of available api functions [`here`](../configuration/dooit_api.md)

### Old

```py
keybindings = {
    "switch pane": "<tab>",
    "sort menu toggle": "<ctrl+s>",
    "start search": ["/", "S"],
    "remove item": "xx",
    "edit effort": "e",
    "edit recurrence": "r",
}
```

### New

```py
@subscribe(Startup)
def key_setup(api: DooitAPI, _):
    api.keys.set("j", api.move_down)
    api.keys.set("k", api.move_up)
    api.keys.set("i", api.edit_description)
    api.keys.set("d", api.edit_due)
    api.keys.set("r", api.edit_recurrence)
    api.keys.set("a", api.add_sibling)
    api.keys.set("z", api.toggle_expand)
    api.keys.set("Z", api.toggle_expand_parent)
    api.keys.set("gg", api.go_to_top)
    api.keys.set("G", api.go_to_bottom)
    api.keys.set("A", api.add_child_node)
    api.keys.set("J", api.shift_down)
    api.keys.set("K", api.shift_up)
    api.keys.set("xx", api.remove_node)
    api.keys.set("c", api.toggle_complete)
    api.keys.set("=,+", api.increase_urgency)
    api.keys.set("-,_", api.decrease_urgency)
    api.keys.set("/", api.start_search)
    api.keys.set("<ctrl+s>", api.start_sort)
```
