from copy import deepcopy

from pytest import raises

from dooit.config.config import AppConfig
from dooit.config.errors import ConfigError, ConfigValidationError
from dooit.config.reader import ConfigReader

base_data = ConfigReader()
base_data.load_defaults()


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
