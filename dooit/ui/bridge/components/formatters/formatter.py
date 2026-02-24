from typing import TYPE_CHECKING

from .._base import ApiComponent
from .model_formatters import TodoFormatter, WorkspaceFormatter

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.bridge.dooit_api import DooitAPI


class Formatter(ApiComponent):
    def __init__(self, api: "DooitAPI") -> None:
        self.api = api
        self.todos = TodoFormatter(api)
        self.workspaces = WorkspaceFormatter(api)
