# Dooit Formatters

:::tip :bulb: TIP
Check out [`Dooit Extras' Formatters`](https://dooit-org.github.io/dooit-extras/formatters/description.html) for cool formatters
:::


## What are formatters?

Formatters are, _simply put_, functions to modify the content you're seeing by default on dooit

For example, by default you see the `due` column values in format DD-MM-YYY but if you'd want to change it, you can use a formatter

Some of the reasons you might use a formatter:

- `styling text`
- `adding extra info`

You can find a [a wide range of formatters](https://dooit-org.github.io/dooit-extras/formatters/description.html) in dooit extras

## Creating formatters

For creating a formatter, you define a function which takes in:

:::tip :bulb: TIP
Check out [`Backend API`](../backend/introduction.md) to get the know about the value types
:::

- `value` -> The real value of the object (for e.g., `due` will be a `datetime` object, `description` will be a `str`)
- `model` -> The respective `Todo` or `Project` object
- `api` [Optional] -> The dooit api 

and returns an optional `str`/`Text` value to be rendered

:::info :grey_exclamation: NOTE
`api` paramater is optional and can be excluded if not necessary
:::

:::tip :bulb: PRO-TIP
You can also return nothing, in that case, dooit will use the previous formatter that was added
For example, if you add 2 formatters, if the later one returns nothing, the former would be used
:::

### An example formatter to format due into a readable format:

```python
from datetime import datetime
from dooit.api import Todo

def my_custom_due(due: datetime, model: Todo) -> str:
    if due.year != datetime.today().year:
        return due.strftime("%b %d, %Y")
    else:
        return due.strftime("%b %d")
```

For example the date is `30-12-2024`, then this function will return `Dec 30, 2024` if the current year is not 2024 else `Dec 30`

### An example formatter to highlight all words in description that starts with `!` symbol

```python
from dooit.api import Todo
from dooit.ui.api import DooitAPI
from rich.text import Text

def redify_important(description: str, model: Todo, api: DooitAPI) -> Text:
    regex = r"!([\w]+)"
    text = Text(description)
    text.highlight_regex(regex, style = api.vars.theme.red)
    return text
```

## Using formatters

Adding a formatter is pretty straightforward, and in this format:

`api.formatter.<todos or projects>.<name of the column>.add(<your function>)`

:::tip
Check out [`Layout`](./layout) Section for column names
:::


```py
from dooit.ui.api import DooitAPI, subscribe
from dooit.ui.api.events import Startup
from rich.text import Text

@subscribe(Startup)
def set_formatters(api: DooitAPI, _):
    fmt = api.formatter

    fmt.projects.description.add(redify_important)
    fmt.todos.description.add(redify_important)
    fmt.todos.due.add(my_custom_due)
```

## Enable/Disable/Remove Formatters

You can also temporarily enable/disable or remove the formatters with formatter ids \
i.e. while adding a formatter, you can pass an id:

```py
from dooit.ui.api import DooitAPI, subscribe
from dooit.ui.api.events import Startup
from rich.text import Text

@subscribe(Startup)
def set_formatters(api: DooitAPI, _):
    fmt = api.formatter

    fmt.projects.description.add(redify_important, id = "redify_important")
    fmt.todos.description.add(redify_important, id = "redify_important")
    fmt.todos.due.add(my_custom_due, "my_due")

    fmt.projects.description.disable("redify_important")
    fmt.projects.description.enable("redify_important")
    fmt.todos.description.remove("redify_important")
```

:::details Combining Multiple formatters :fire:

> [!NOTE]
> You can still apply all your customization within one formatter, this section can be a bit for developer friendly and for people who'd like to ship their own formatters
>
> If you're still interested, lets go (I'll try to keep it as simple as possible)

There are two types of formattters:

- First one take in the original value and convert into a custom string value to be shown, after it has converted to a string value, its difficult to further modify it since we wont know the original value (even if we know and change it, then we'd completely override the first format )

For example, lets take the [`my_custom_due`](#an-example-formatter-to-format-due-into-a-readable-format) formatter defined above,

Suppose, the due date is a datetime object for date `31-12-2024`, but after formatting, it changed to `31 Dec`

Now the second formatter will see this value instead of the datetime object.

- Now here comes the role of second formatter, it does not change the value of text, but accepts a string and modified it by adding more data. \
A good example would be [`Due Icons Formatter`](https://dooit-org.github.io/dooit-extras/formatters/due.html#due-icon) from dooit extras
It is similiar to first type of formatter except a few changes:

   - The first `value` paramter is string instead of the original data
   - You need to add the `@extra_formatter` decorator

An example:

```py
from dooit.ui.api import DooitAPI, subscribe, extra_formatter
from dooit.ui.api.events import Startup

@extra_formatter
def due_icon(due: str, model: Todo) -> str:
    return f"📅 {due}"

@subscribe(Startup)
def set_formatters(api: DooitAPI, _):
    api.formatter.todos.due.add(due_icon)
```
:::
