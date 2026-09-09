from typing import TYPE_CHECKING

from .._base import ApiComponent
from .model_formatters import TodoFormatter, ProjectFormatter

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


class Formatter(ApiComponent):
    def __init__(self, api: "DooitAPI") -> None:
        self.todos = TodoFormatter(api)
        self.projects = ProjectFormatter(api)
        self.app = api
