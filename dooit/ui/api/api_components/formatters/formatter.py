from typing import TYPE_CHECKING

from .._base import ApiComponent
from .model_formatters import TodoFormatter, WorkspaceFormatter

if TYPE_CHECKING:  # pragma: no cover
    from dooit.ui.api.dooit_api import DooitAPI


class Formatter(ApiComponent):
    """
    Top-level API component that exposes formatter stores for todos and workspaces.

    Acts as a container providing access to TodoFormatter and WorkspaceFormatter
    instances, allowing users to register custom formatting functions for model fields.
    """

    def __init__(self, api: "DooitAPI") -> None:
        self.todos = TodoFormatter(api)
        self.workspaces = WorkspaceFormatter(api)
        self.app = api
