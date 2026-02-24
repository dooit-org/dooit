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

A formatter is a function that takes in the `Todo` or `Workspace` model and returns a `str` or `Text` value to be rendered.

:::tip :bulb: TIP
Check out [`Backend API`](../backend/introduction.md) to get the know about the model fields
:::

### An example formatter to format due into a readable format:

```python
from datetime import datetime
from dooit.models import Todo

def my_custom_due(todo: Todo) -> str:
    if not todo.due:
        return ""
    if todo.due.year != datetime.today().year:
        return todo.due.strftime("%b %d, %Y")
    else:
        return todo.due.strftime("%b %d")
```

For example the date is `30-12-2024`, then this function will return `Dec 30, 2024` if the current year is not 2024 else `Dec 30`

### An example formatter to highlight all words in description that starts with `!` symbol

```python
from dooit.models import Todo
from rich.text import Text

def redify_important(todo: Todo) -> Text:
    regex = r"!([\w]+)"
    text = Text(todo.description)
    text.highlight_regex(regex, style="red")
    return text
```

## Using formatters

Adding a formatter is pretty straightforward, and in this format:

`api.formatter.<todos or workspaces>.<name of the column>.add(<your function>)`

:::tip
Check out [`Layout`](./layout) Section for column names
:::


```py
from dooit.ui.bridge import DooitAPI, subscribe
from dooit.ui.bridge.events import Startup

@subscribe(Startup)
def set_formatters(api: DooitAPI, _):
    fmt = api.formatter

    fmt.workspaces.description.add(redify_important)
    fmt.todos.description.add(redify_important)
    fmt.todos.due.add(my_custom_due)
```
