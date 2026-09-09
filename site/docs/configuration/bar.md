# Dooit Bar

You can customize your dooit bar using widgets!

:::tip :bulb: TIP
Check out [dooit-extras' widgets](https://dooit-org.github.io/dooit-extras/widgets/current_project.html)
:::

## Using widgets

Dooit's api provides `bar` attribute to set bar widgets

### Usage:

```python
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

This will render a bar like this: 

![Sample Bar](./imgs/sample_bar.png)

:::tip :bulb: TIP

If you want to create your own widget that displays some information based on a function, you can use [`Custom`](https://dooit-org.github.io/dooit-extras/widgets/custom.html) widget from dooit_extras

If you want to take it further and totally create from scratch, have a look at [`BarUtilWidgetBase`](https://github.com/dooit-org/dooit-extras/blob/1f442ed6e6b98d53aa20e5ab8a64e59ef2f3abdb/dooit_extras/bar_widgets/_base.py#L9)
