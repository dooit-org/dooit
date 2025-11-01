from pathlib import Path
from typing import final, override
from textual import on
from textual.app import App
from textual.binding import Binding
from dooit.ui.api.events import (
    ModeChanged,
    DooitEvent,
    ModeType,
    Startup,
    QuitApp,
    ShutDown,
)
from dooit.ui.widgets import BarSwitcher
from dooit.ui.widgets.bars import StatusBar
from dooit.ui.widgets.trees import WorkspacesTree
from dooit.ui.screens import MainScreen, HelpScreen
from dooit.ui.widgets.trees.model_tree import ModelTree
from dooit.utils import CssManager
from .api import DooitAPI
from ..api import manager
from dooit.config import ConfigManager, ConfigService

PRINTABLE = (
    "0123456789"
    + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    + "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ "
)


@final
class Dooit(App[None]):
    CSS_PATH = CssManager().css_file
    ENABLE_COMMAND_PALETTE = False

    SCREENS = {
        "help": HelpScreen,
        "main": MainScreen,
    }
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
    ]

    def __init__(self, db_path: Path, config_path: Path):
        super().__init__(watch_css=True)
        self.api: DooitAPI
        self.config_service: ConfigService

        self.dooit_mode: ModeType = "NORMAL"
        self.config_path = config_path
        manager.connect_to_path(db_path)

    async def setup_poller(self):
        self.set_interval(1, self.poll_dooit_db)

    async def on_mount(self):
        self.api = DooitAPI(self)
        self.config_service = ConfigService(self.api)
        self.config_service.load_file(self.config_path)
        self.config_service.apply_config()

        self.post_message(Startup())
        self.post_message(ModeChanged("NORMAL"))
        self.push_screen("main")

        await self.setup_poller()

    @override
    async def action_quit(self) -> None:
        self.post_message(ShutDown())
        return await super().action_quit()

    @property
    def workspace_tree(self) -> WorkspacesTree:
        return self.screen.query_one(WorkspacesTree)

    @property
    def bar(self) -> StatusBar:
        return self.screen.query_one(BarSwitcher).status_bar

    @property
    def bar_switcher(self) -> BarSwitcher:
        return self.screen.query_one(BarSwitcher)

    def get_dooit_mode(self) -> ModeType:
        return self.dooit_mode

    async def poll_dooit_db(self):  # pragma: no cover
        def refresh_all_trees():
            trees = self.screen.query(ModelTree)
            for tree in trees:
                tree.force_refresh()

        if manager.has_changed():
            refresh_all_trees()

    @on(DooitEvent)
    def global_message(self, event: DooitEvent):
        if isinstance(self.screen, MainScreen):
            self.api.trigger_event(event)
            self.bar.refresh()

    @on(ShutDown)
    def shutdown(self, _: ShutDown):
        self.api.css.cleanup()

    @on(ModeChanged)
    def change_status(self, event: ModeChanged):
        self.dooit_mode = event.mode
        if event.mode == "NORMAL":
            self.workspace_tree.refresh_options()
            todos_tree = self.api.vars.todos_tree
            if todos_tree:
                todos_tree.refresh_options()

    @on(QuitApp)
    async def quit_app(self):
        await self.action_quit()

    async def action_open_url(self, url: str) -> None:  # pragma: no cover
        self.open_url(url)


if __name__ == "__main__":  # pragma: no cover
    Dooit().run()
