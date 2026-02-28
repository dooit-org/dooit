from copy import deepcopy
from logging import raiseExceptions
from pathlib import Path

import tomllib
from pytest import raises

from dooit.config.config import AppConfig
from dooit.config.errors import ConfigError, ConfigValidationError
from dooit.config.reader import ConfigReader

base_data = ConfigReader()
base_data.load_defaults()


def test_override_merge():
    data = deepcopy(base_data)
    old = data["formatter"]["todo"]["description"]["format"]
    assert (
        data["formatter"]["todo"]["description"]["highlighted"]["css"]["bold"] == True
    )

    sample_config = """
    [formatter.todo.description]
    highlighted.css.bold = false
    css.color = "$red"
    css.bold = true
    """

    extra_data = tomllib.loads(sample_config)
    data.merge(ConfigReader.from_dict(extra_data, Path(__file__)))

    assert (
        data["formatter"]["todo"]["description"]["highlighted"]["css"]["bold"] == False
    )

    assert data["formatter"]["todo"]["description"]["format"] == old


def test_incorect_color():
    data = deepcopy(base_data)
    data["script"]["mode"]["normal"]["css"]["backrgound"] = " $non_existent_color "

    with raises(KeyError):
        AppConfig.from_resolved(data)


def test_script_missing_script_param():
    data = deepcopy(base_data)
    data["script"]["mode"].pop("_script")

    with raises(ConfigError):
        AppConfig.from_resolved(data)


def test_script_incorrect_script_param():
    data = deepcopy(base_data)
    data["script"]["mode"]["_script"] = "./non_exitstend:not_there"

    with raises(ConfigValidationError):
        AppConfig.from_resolved(data)


def test_invalid_refresh_value():
    data = deepcopy(base_data)
    data["script"]["mode"]["_refresh"] = "padh le bhai"

    with raises(ConfigValidationError):
        AppConfig.from_resolved(data)


def test_invalid_refresh_interval():
    data = deepcopy(base_data)
    data["script"]["mode"]["_refresh"] = "every 9s"
    AppConfig.from_resolved(data)

    data["script"]["mode"]["_refresh"] = "every 9x"

    with raises(ConfigValidationError):
        AppConfig.from_resolved(data)


def test_reload_targets():
    data = deepcopy(base_data)
    extra_config = """
    [script.mode]
    css.color = "$red"
    css.bold = true
    _reload = "bar"
    """

    extra_data = tomllib.loads(extra_config)
    data.merge(ConfigReader.from_dict(extra_data, Path(__file__)))

    config = AppConfig.from_resolved(data)
    assert config.script["mode"].entry.reload_targets == {"bar"}


def test_reload_targets_invalid():
    data = deepcopy(base_data)
    extra_config = """
    [script.mode]
    css.color = "$red"
    css.bold = true
    _reload = ["bar"]
    """

    extra_data = tomllib.loads(extra_config)
    data.merge(ConfigReader.from_dict(extra_data, Path(__file__)))

    with raises(ConfigValidationError, match="comma separated string"):
        AppConfig.from_resolved(data)


def test_refresh_invalid():
    data = deepcopy(base_data)
    extra_config = """
    [script.mode]
    css.color = "$red"
    css.bold = true
    _refresh = "on "
    """

    extra_data = tomllib.loads(extra_config)
    data.merge(ConfigReader.from_dict(extra_data, Path(__file__)))

    with raises(
        ConfigValidationError, match="Event name cannot be empty in refresh config"
    ):
        AppConfig.from_resolved(data)


def test_refresh_invalid_event():
    data = deepcopy(base_data)
    extra_config = """
    [script.mode]
    css.color = "$red"
    css.bold = true
    _refresh = "on UnknownEvent"
    """

    extra_data = tomllib.loads(extra_config)
    data.merge(ConfigReader.from_dict(extra_data, Path(__file__)))

    with raises(ConfigValidationError, match="not found for refresh config"):
        AppConfig.from_resolved(data)
