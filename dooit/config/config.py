from enum import Enum

import msgspec

from dooit.config.utils import ScriptParser

S = dict(kw_only=True, frozen=True)


class TodoField(str, Enum):
    DESCRIPTION = "description"
    DUE = "due"
    URGENCY = "urgency"
    RECURRENCE = "recurrence"
    STATUS = "status"
    EFFORT = "effort"


class WorkspaceField(str, Enum):
    DESCRIPTION = "description"


class ThemeColors(msgspec.Struct, **S):
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

    def as_dict(self) -> dict:
        return msgspec.structs.asdict(self)


class GeneralConfig(msgspec.Struct, **S):
    theme: str


class LayoutConfig(msgspec.Struct, **S):
    todo: list[TodoField]
    workspace: list[WorkspaceField]


class KeysConfig(msgspec.Struct, forbid_unknown_fields=True, **S):
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


class BarConfig(msgspec.Struct, **S):
    widgets_left: list[str]
    widgets_right: list[str]


class DashboardConfig(msgspec.Struct, **S):
    widgets: list[str]


class AppConfig(msgspec.Struct, kw_only=True):
    general: GeneralConfig
    theme: dict[str, ThemeColors]
    layout: LayoutConfig
    keys: KeysConfig
    bar: BarConfig
    dashboard: DashboardConfig
    script: dict
    formatter: dict

    @classmethod
    def from_resolved(cls, data: dict) -> "AppConfig":
        """Create from already-resolved ConfigData/dict."""
        config = msgspec.convert(data, cls)
        config.resolve_scripts()
        return config

    def get_active_theme(self) -> ThemeColors:
        return self.theme[self.general.theme]

    def resolve_scripts(self):
        for script_name, script_entry in self.script.items():
            if isinstance(script_entry, dict):
                self.script[script_name] = ScriptParser.parse_script_entry(script_entry)

    def get_scripts(self) -> dict:
        return self.script
