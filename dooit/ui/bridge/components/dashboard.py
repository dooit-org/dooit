from dooit.config import AppConfig, ScriptField

from ._base import ApiComponent


class DashboardManager(ApiComponent):
    def __init__(self) -> None:
        super().__init__()
        self.widgets: list[ScriptField] = []

    @classmethod
    def from_config(cls, config: AppConfig):
        instance = cls()
        scripts = config.get_scripts()

        dashboard_config = config.dashboard
        widgets = [scripts[name] for name in dashboard_config.widgets]
        instance.set(widgets)

        return instance

    def set(self, funcs: list[ScriptField]) -> None:
        self.widgets = funcs
