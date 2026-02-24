from enum import Enum
from typing import Any

import msgspec

from dooit.config.script_parser import ScriptParser
from dooit.models import DooitModel

S = dict(kw_only=True, frozen=True)


class BaseConfigType(msgspec.Struct, forbid_unknown_fields=True, **S):
    def as_dict(self) -> dict:
        return msgspec.structs.asdict(self)


# --- theme ---
class ThemeColors(BaseConfigType):
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

    @classmethod
    def nord(cls) -> "ThemeColors":
        return cls(
            background1="#2E3440",
            background2="#3B4252",
            background3="#434C5E",
            foreground1="#D8DEE9",
            foreground2="#E5E9F0",
            foreground3="#ECEFF4",
            red="#BF616A",
            orange="#D08770",
            yellow="#EBCB8B",
            green="#A3BE8C",
            blue="#81A1C1",
            purple="#B48EAD",
            magenta="#88C0D0",
            cyan="#8FBCBB",
            primary="#81A1C1",
            secondary="#88C0D0",
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


class LayoutConfig(BaseConfigType):
    todo: list[TodoField]
    workspace: list[WorkspaceField]


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
        self._cached = "N/A"

    def __call__(self, params: dict[str, Any]):
        self._cached = self.entry.func(**params, context=self.entry.context)


class AppConfig(msgspec.Struct, kw_only=True):
    general: GeneralConfig
    theme: dict[str, ThemeColors]
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

            raise TypeError(f"Cannot convert {type(obj)} to {typ}")

        return msgspec.convert(data, cls, dec_hook=dec_hook)

    def get_active_theme(self) -> ThemeColors:
        return self.theme[self.general.theme]

    def get_scripts(self) -> dict:
        return self.script
