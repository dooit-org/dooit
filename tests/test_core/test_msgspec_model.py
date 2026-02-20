import msgspec
import pytest

from dooit.config import AppConfig


@pytest.fixture
def valid_data():
    return {
        "general": {"theme": "nord"},
        "theme": {
            "nord": {
                "background1": "#2E3440",
                "background2": "#3B4252",
                "background3": "#434C5E",
                "foreground1": "#D8DEE9",
                "foreground2": "#E5E9F0",
                "foreground3": "#ECEFF4",
                "red": "#BF616A",
                "orange": "#D08770",
                "yellow": "#EBCB8B",
                "green": "#A3BE8C",
                "blue": "#81a1c1",
                "purple": "#B48EAD",
                "magenta": "#B48EAD",
                "cyan": "#8fbcbb",
            }
        },
        "layout": {
            "todo": ["status", "description", "due", "urgency"],
            "workspace": ["description"],
        },
        "keys": {
            "switch_focus": "<tab>",
            "move_down": "j",
            "move_up": "k",
            "edit_description": "i",
            "edit_due": "d",
            "edit_recurrence": "r",
            "edit_effort": "e",
            "add_sibling": "a",
            "toggle_expand": "z",
            "toggle_expand_parent": "Z",
            "go_to_top": "gg",
            "go_to_bottom": "G",
            "add_child_node": "A",
            "shift_down": "J",
            "shift_up": "K",
            "remove_node": "xx",
            "copy_description_to_clipboard": "y",
            "copy_model": "Y",
            "paste_model_below": "p",
            "paste_model_above": "P",
            "toggle_complete": "c",
            "increase_urgency": ["=", "+"],
            "decrease_urgency": ["-", "_"],
            "start_search": "/",
            "start_sort": "<ctrl+s>",
            "quit": "<ctrl+q>",
            "show_help": "?",
        },
        "bar": {"widgets_left": ["mode"], "widgets_right": ["clock", "user"]},
        "dashboard": {"widgets": ["qoute", "ascii"]},
        "script": {},
        "formatter": {},
    }


def test_successful_parse(valid_data):
    config = AppConfig.from_resolved(valid_data)
    assert config.general.theme == "nord"
    assert config.get_active_theme().red == "#BF616A"
    assert config.keys.quit == "<ctrl+q>"
    assert config.keys.increase_urgency == ["=", "+"]
    assert len(config.layout.todo) == 4
    assert config.bar.widgets_right == ["clock", "user"]


def test_invalid_layout_field(valid_data):
    valid_data["layout"]["todo"] = ["status", "bananas"]
    with pytest.raises(msgspec.ValidationError, match="bananas"):
        AppConfig.from_resolved(valid_data)


def test_invalid_key_function(valid_data):
    valid_data["keys"]["fly_to_moon"] = "x"
    with pytest.raises(msgspec.ValidationError, match="fly_to_moon"):
        AppConfig.from_resolved(valid_data)
