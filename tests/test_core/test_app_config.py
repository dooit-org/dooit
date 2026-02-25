from pytest import raises

from dooit.config.config import AppConfig

base_data = {
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
            "primary": "#8fbcbb",
            "secondary": "#81a1c1",
        }
    },
    "general": {"theme": "nord"},
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
    "formatter": {
        "workspace": {
            "description": {
                "_script": "../dooit/dooit/config/default/formatters.py::workspace_description",
                "format": "{description}",
                "format_with_child": "{description} ({child_count})",
                "highlighted": {"css": {"bold": True}},
            }
        },
        "todo": {
            "description": {
                "_script": "../dooit/dooit/config/default/formatters.py::todo_description",
                "format": "{description}",
                "format_with_child": "{description} ({child_count})",
                "highlighted": {"css": {"bold": True}},
            },
            "status": {
                "_script": "../dooit/dooit/config/default/formatters.py::todo_status",
                "pending": {"format": "o", "css": {"color": "$yellow"}},
                "completed": {"format": "x", "css": {"color": "$green"}},
                "overdue": {"format": "o", "css": {"color": "$red"}},
            },
            "due": {
                "_script": "../dooit/dooit/config/default/formatters.py::todo_due",
                "format": "{due_date}",
                "format_string": "%Y-%m-%d",
                "format_string_with_time": "%Y-%m-%d %H:%M",
                "highlighted": {"css": {"bold": True}},
            },
            "urgency": {
                "_script": "../dooit/dooit/config/default/formatters.py::todo_urgency",
                "a": {"format": "(!)1", "css": {"color": "$red"}},
                "b": {"format": "(!)2", "css": {"color": "$orange"}},
                "c": {"format": "(!)3", "css": {"color": "$yellow"}},
                "d": {"format": "(!)4", "css": {"color": "$green"}},
                "highlighted": {"css": {"bold": True}},
            },
            "effort": {
                "_script": "../dooit/dooit/config/default/formatters.py::todo_effort",
                "format": "{effort}",
                "css": {"color": "$orange"},
                "highlighted": {"css": {"bold": True}},
            },
            "recurrence": {
                "_script": "../dooit/dooit/config/default/formatters.py::todo_recurrence",
                "format": "{recurrence}",
                "css": {"color": "$cyan"},
                "highlighted": {"css": {"bold": True}},
            },
        },
    },
    "bar": {"widgets_left": ["mode"], "widgets_right": ["clock", "pad", "user"]},
    "dashboard": {"widgets": ["qoute", "ascii"]},
    "script": {
        "mode": {
            "_script": "../dooit/dooit/config/default/scripts::mode",
            "_refresh": "on ModeChanged",
            "normal": {
                "format": " NOR ",
                "css": {"color": "$background2", "background": "$primary"},
            },
            "insert": {
                "format": " INS ",
                "css": {"color": "$background2", "background": "$secondary"},
            },
        },
        "clock": {
            "_script": "../dooit/dooit/config/default/scripts::clock",
            "_refresh": "every 1s",
            "format": " %H:%M:%S ",
            "css": {"color": "$background2", "background": "$primary"},
        },
        "user": {
            "_script": "../dooit/dooit/config/default/scripts::user",
            "format": " {username} ",
            "css": {"color": "$background2", "background": "$secondary"},
        },
        "qoute": {
            "_script": "../dooit/dooit/config/default/scripts::qoute",
            "format": "{qoute}",
            "css": {"color": "$secondary"},
        },
        "ascii": {
            "_script": "../dooit/dooit/config/default/scripts::ascii",
            "format": "{ascii_art}",
            "css": {"color": "$primary"},
        },
        "pad": {"_script": "../dooit/dooit/config/default/scripts::small_pad"},
    },
}


def test_incorect_color():
    data = base_data.copy()
    data["script"]["mode"]["normal"]["css"]["backrgound"] = " $non_existent_color "

    with raises(KeyError):
        AppConfig.from_resolved(data)
