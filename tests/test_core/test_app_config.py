from pytest import raises

from dooit.config.config import AppConfig
from dooit.config.reader import ConfigReader

base_data = ConfigReader()
base_data.load_defaults()


def test_incorect_color():
    data = base_data.copy()
    data["script"]["mode"]["normal"]["css"]["backrgound"] = " $non_existent_color "

    with raises(KeyError):
        AppConfig.from_resolved(data)
