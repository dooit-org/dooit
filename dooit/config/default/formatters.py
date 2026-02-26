from rich.style import Style
from rich.text import Text

from dooit.models import Todo, Workspace


def build_style(css: dict) -> Style:
    return Style(
        color=css.get("color"),
        bgcolor=css.get("background"),
        bold=css.get("bold"),
        italic=css.get("italic"),
    )


def workspace_description(workspace: Workspace, context: dict) -> Text:
    if child_count := len(workspace.workspaces):
        text = context["format_with_child"].format(
            description=workspace.description, child_count=child_count
        )
    else:
        text = context["format"].format(description=workspace.description)

    return Text(text)


def todo_description(todo: Todo, context: dict) -> Text:
    if child_count := len(todo.todos):
        text = context["format_with_child"].format(
            description=todo.description, child_count=child_count
        )
    else:
        text = context["format"].format(description=todo.description)

    return Text(text)


def todo_status(todo: Todo, context: dict) -> Text:
    status = todo.status.lower()
    settings = context[status]
    return Text(settings["format"], style=build_style(settings["css"]))


def todo_urgency(todo: Todo, context: dict) -> Text:
    if not todo.urgency:
        return Text("")

    settings = context[str(todo.urgency).lower()]
    return Text(settings["format"], style=build_style(settings["css"]))


def todo_due(todo: Todo, context: dict) -> Text:
    if not todo.due:
        return Text("")

    status = todo.status
    settings = context[status]
    format = settings["format"]

    if todo.due:
        if todo.due.hour or todo.due.minute:
            fmt_str = context["date_format"]
        else:
            fmt_str = context["date_format_with_time"]

        due_str = todo.due.strftime(fmt_str)
    else:
        due_str = "-"

    text = format.format(date=due_str)
    return Text(text, style=build_style(settings["css"]))


def todo_effort(todo: Todo, context: dict) -> Text:
    if not todo.effort:
        return Text("")

    text = context["format"].format(effort=todo.effort)
    return Text(text, style=build_style(context["css"]))


def todo_recurrence(todo: Todo, context: dict) -> Text:
    if not todo.recurrence:
        return Text("")

    text = context["format"].format(recurrence=todo.recurrence)
    return Text(text, style=build_style(context["css"]))
