from enum import Enum

import msgspec

from dooit.api import DooitModel

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

    def __call__(self, model: DooitModel) -> str:
        return str(model)


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
class ScriptEntry:
    def __init__(self, config: dict):
        self.config = config

    def __call__(self, model: DooitModel) -> str:
        raise NotImplementedError
