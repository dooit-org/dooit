import pytest

from dooit.config.errors import ConfigError, ConfigValidationError
from dooit.config.utils import ConfigData
from dooit.config.validator import ConfigValidator


def _make_config(data: dict) -> ConfigData:
    return ConfigData.from_dict(data)


def _minimal_valid_config(**overrides: object) -> dict:
    """Return the smallest config that passes all validator checks."""
    base: dict = {
        "general": {"theme": "default"},
        "theme": {"default": {"background1": "#000"}},
    }
    base.update(overrides)
    return base


# --- _validate_general ---


def test_missing_general_section():
    config = _make_config({"theme": {"default": {}}})
    with pytest.raises(ConfigError, match=r"Missing \[general\] section"):
        ConfigValidator(config).validate()


def test_general_not_a_dict():
    config = _make_config({"general": "oops", "theme": {"default": {}}})
    with pytest.raises(ConfigError, match=r"Missing \[general\] section"):
        ConfigValidator(config).validate()


def test_missing_theme_key_in_general():
    config = _make_config({"general": {"other": "value"}, "theme": {"default": {}}})
    with pytest.raises(ConfigError, match=r"Missing 'theme' key"):
        ConfigValidator(config).validate()


# --- _validate_theme ---


def test_theme_not_found():
    config = _make_config({"general": {"theme": "nonexistent"}, "theme": {"nord": {}}})
    with pytest.raises(ConfigError, match=r"Theme 'nonexistent' not found"):
        ConfigValidator(config).validate()


def test_theme_not_found_empty_themes():
    config = _make_config({"general": {"theme": "anything"}})
    with pytest.raises(ConfigError, match=r"Available themes: \(none\)"):
        ConfigValidator(config).validate()


# --- _validate_formatters ---


def test_formatter_section_not_a_table():
    config = _make_config(_minimal_valid_config(formatter="bad"))
    with pytest.raises(ConfigValidationError, match=r"\[formatter\] must be a table"):
        ConfigValidator(config).validate()


def test_formatter_model_type_not_a_table():
    config = _make_config(_minimal_valid_config(formatter={"todo": "bad"}))
    with pytest.raises(
        ConfigValidationError, match=r"\[formatter\.todo\] must be a table"
    ):
        ConfigValidator(config).validate()


def test_formatter_field_not_a_table():
    config = _make_config(
        _minimal_valid_config(formatter={"todo": {"status": "bad"}})
    )
    with pytest.raises(
        ConfigValidationError, match=r"\[formatter\.todo\.status\] must be a table"
    ):
        ConfigValidator(config).validate()


def test_valid_formatter_structure():
    config = _make_config(
        _minimal_valid_config(
            formatter={"todo": {"status": {"_script": "dummy", "format": "{s}"}}}
        )
    )
    ConfigValidator(config).validate()


# --- _validate_scripts ---


def test_script_section_not_a_table():
    config = _make_config(_minimal_valid_config(script="bad"))
    with pytest.raises(ConfigValidationError, match=r"\[script\] must be a table"):
        ConfigValidator(config).validate()


def test_script_entry_not_a_table():
    config = _make_config(_minimal_valid_config(script={"clock": "bad"}))
    with pytest.raises(
        ConfigValidationError, match=r"\[script\.clock\] must be a table"
    ):
        ConfigValidator(config).validate()


def test_script_missing_script_key():
    config = _make_config(
        _minimal_valid_config(script={"clock": {"format": "%H:%M"}})
    )
    with pytest.raises(ConfigError, match=r"\[script\.clock\] is missing a '_script'"):
        ConfigValidator(config).validate()


def test_valid_script_section():
    config = _make_config(
        _minimal_valid_config(
            script={"clock": {"_script": "./scripts.py::clock", "format": "%H:%M"}}
        )
    )
    ConfigValidator(config).validate()


# --- _validate_bar_widgets ---


def test_bar_widget_references_missing_script():
    config = _make_config(
        _minimal_valid_config(
            bar={"widgets_left": ["mode"], "widgets_right": []},
            script={"clock": {"_script": "./s.py::c"}},
        )
    )
    with pytest.raises(
        ConfigError,
        match=r"\[bar\] references script 'mode'.*no \[script\.mode\] section",
    ):
        ConfigValidator(config).validate()


def test_bar_widget_right_references_missing_script():
    config = _make_config(
        _minimal_valid_config(
            bar={"widgets_left": [], "widgets_right": ["missing"]},
            script={"clock": {"_script": "./s.py::c"}},
        )
    )
    with pytest.raises(ConfigError, match=r"\[bar\] references script 'missing'"):
        ConfigValidator(config).validate()


def test_valid_bar_widgets():
    config = _make_config(
        _minimal_valid_config(
            bar={"widgets_left": ["mode"], "widgets_right": ["clock"]},
            script={
                "mode": {"_script": "./s.py::mode"},
                "clock": {"_script": "./s.py::clock"},
            },
        )
    )
    ConfigValidator(config).validate()


# --- _validate_dashboard_widgets ---


def test_dashboard_widget_references_missing_script():
    config = _make_config(
        _minimal_valid_config(
            dashboard={"widgets": ["quote"]},
            script={"clock": {"_script": "./s.py::c"}},
        )
    )
    with pytest.raises(
        ConfigError,
        match=r"\[dashboard\] references script 'quote'",
    ):
        ConfigValidator(config).validate()


def test_valid_dashboard_widgets():
    config = _make_config(
        _minimal_valid_config(
            dashboard={"widgets": ["quote"]},
            script={"quote": {"_script": "./s.py::quote"}},
        )
    )
    ConfigValidator(config).validate()


# --- full pass ---


def test_minimal_valid_config_passes():
    config = _make_config(_minimal_valid_config())
    ConfigValidator(config).validate()


def test_empty_optional_sections_pass():
    config = _make_config(
        _minimal_valid_config(
            formatter={},
            script={},
            bar={},
            dashboard={},
            keys={},
            layout={},
        )
    )
    ConfigValidator(config).validate()
