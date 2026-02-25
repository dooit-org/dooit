from enum import Enum
from string import Template
from typing import Any

import msgspec

from dooit.config.script_parser import ScriptParser
from dooit.models import DooitModel

S = dict(kw_only=True)


class BaseConfigType(msgspec.Struct, forbid_unknown_fields=True, **S):
    def as_dict(self) -> dict:
        return msgspec.structs.asdict(self)


# --- theme ---
class DooitTheme(BaseConfigType):
    """
    Theme colors for dooit (all hex codes)
    """

    background1: str
    background2: str
    background3: str
    foreground1: str
    foreground2: str
    foreground3: str
    red: str
    orange: str
    yellow: str
    green: str
    blue: str
    purple: str
    magenta: str
    cyan: str

    primary: str
    secondary: str

    def to_css(self) -> str:
        return (
            f"$background1: {self.background1};\n"
            f"$background2: {self.background2};\n"
            f"$background3: {self.background3};\n"
            f"$foreground1: {self.foreground1};\n"
            f"$foreground2: {self.foreground2};\n"
            f"$foreground3: {self.foreground3};\n"
            f"$red: {self.red};\n"
            f"$orange: {self.orange};\n"
            f"$yellow: {self.yellow};\n"
            f"$green: {self.green};\n"
            f"$blue: {self.blue};\n"
            f"$purple: {self.purple};\n"
            f"$magenta: {self.magenta};\n"
            f"$primary: {self.primary};\n"
            f"$secondary: {self.secondary};\n"
        )


# --- general ---
class GeneralConfig(BaseConfigType):
    """
    All the stuff that goes into general section
    """

    theme: str


# --- layout ---
class TodoField(str, Enum):
    """
    Enum for todo layout
    """

    DESCRIPTION = "description"
    DUE = "due"
    URGENCY = "urgency"
    RECURRENCE = "recurrence"
    STATUS = "status"
    EFFORT = "effort"


class WorkspaceField(str, Enum):
    """
    Enum for workspace layout
    """

    DESCRIPTION = "description"


class BaseConfigLayout(BaseConfigType):
    columns: list[TodoField]
    description: int = 0


class TodoLayoutConfig(BaseConfigLayout):
    due: int = 25
    urgency: int = 1
    recurrence: int = 4
    status: int = 1
    effort: int = 3


class WorkspaceLayoutConfig(BaseConfigLayout):
    pass


class LayoutConfig(BaseConfigType):
    todo: TodoLayoutConfig
    workspace: WorkspaceLayoutConfig


# --- layout ---
class KeysConfig(BaseConfigType):
    switch_focus: str
    move_down: str
    move_up: str
    edit_description: str
    edit_due: str
    edit_recurrence: str
    edit_effort: str
    add_sibling: str
    toggle_expand: str
    toggle_expand_parent: str
    go_to_top: str
    go_to_bottom: str
    add_child_node: str
    shift_down: str
    shift_up: str
    remove_node: str
    copy_description_to_clipboard: str
    copy_model: str
    paste_model_below: str
    paste_model_above: str
    toggle_complete: str
    increase_urgency: str | list[str]
    decrease_urgency: str | list[str]
    start_search: str
    start_sort: str
    quit: str
    show_help: str


# --- bar ---
class BarConfig(BaseConfigType):
    widgets_left: list[str]
    widgets_right: list[str]


# --- dashboard ---
class DashboardConfig(BaseConfigType):
    widgets: list[str]


# --- formatters ---
class FieldFormatter:
    def __init__(self, config: dict):
        self.config = config
        self.func = ScriptParser.parse_script_entry(config)

    def __call__(self, model: DooitModel) -> str:
        return self.func.func(model)


class TodoFormatter(BaseConfigType):
    description: FieldFormatter
    due: FieldFormatter
    urgency: FieldFormatter
    recurrence: FieldFormatter
    status: FieldFormatter
    effort: FieldFormatter


class WorkspaceFormater(BaseConfigType):
    description: FieldFormatter


class FormatterConfig(BaseConfigType):
    todo: TodoFormatter
    workspace: WorkspaceFormater


# --- scripts ---
class ScriptField:
    def __init__(self, context: dict):
        self.entry = ScriptParser.parse_script_entry(context)
        self._cached = " "

    def update(self, **params: Any):
        self._cached = self.entry.func(**params, context=self.entry.context)


def resolve_variables(obj: Any, variables: dict[str, str]) -> Any:
    if isinstance(obj, str) and "$" in obj:
        return Template(obj).substitute(variables)
    elif isinstance(obj, dict):
        return {k: resolve_variables(v, variables) for k, v in obj.items()}
    return obj


class AppConfig(msgspec.Struct, kw_only=True):
    general: GeneralConfig
    theme: dict[str, DooitTheme]
    layout: LayoutConfig
    keys: KeysConfig
    bar: BarConfig
    dashboard: DashboardConfig
    formatter: FormatterConfig
    script: dict[str, ScriptField]

    @classmethod
    def from_resolved(cls, data: dict) -> "AppConfig":
        def dec_hook(typ, obj):
            if typ is FieldFormatter:
                return FieldFormatter(obj)
            if typ is ScriptField:
                return ScriptField(obj)

        config = msgspec.convert(data, cls, dec_hook=dec_hook)
        config._resolve_vars()
        return config

    def _resolve_vars(self) -> None:
        theme = self.get_active_theme()
        variables = {
            k: str(v)
            for k, v in msgspec.structs.asdict(theme).items()
            if isinstance(v, str)
        }

        for field in self.script.values():
            field.entry.context = resolve_variables(field.entry.context, variables)

    def get_active_theme(self) -> DooitTheme:
        return self.theme[self.general.theme]

    def get_scripts(self) -> dict:
        return self.script
