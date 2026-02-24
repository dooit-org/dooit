from dooit.config import AppConfig, ScriptField

from ._base import ApiComponent


class BarManager(ApiComponent):
    def __init__(self) -> None:
        super().__init__()
        self.widgets_left = []
        self.widgets_right = []

    def set(self, left: list["ScriptField"], right: list["ScriptField"]):
        self.widgets_left = left
        self.widgets_right = right

    def get(self):
        return self.widgets_left, self.widgets_right

    @classmethod
    def from_config(cls, config: AppConfig) -> "BarManager":
        instance = cls()

        scripts = config.get_scripts()
        bar_config = config.bar

        left = [scripts[name] for name in bar_config.widgets_left]
        right = [scripts[name] for name in bar_config.widgets_right]
        instance.set(left, right)

        return instance
