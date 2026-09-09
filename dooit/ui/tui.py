from pathlib import Path
from typing import Optional
from textual import on
from textual.app import App
from dooit.ui.api.events import ModeChanged, DooitEvent, ModeType, Startup, QuitApp
from dooit.ui.api.events.events import ShutDown
from dooit.ui.widgets import BarSwitcher
from dooit.ui.widgets.bars import StatusBar
from dooit.ui.widgets.trees import ProjectsTree
from dooit.ui.screens import MainScreen, HelpScreen
from dooit.ui.widgets.trees.model_tree import ModelTree
from dooit.utils import CssManager, open_url
from .api import DooitAPI
from ..api import manager, drop_blank_models

PRINTABLE = (
    "0123456789"
    + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    + "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ "
)


class Dooit(App):
    CSS_PATH = CssManager().css_file
    ENABLE_COMMAND_PALETTE = False

    SCREENS = {
        "help": HelpScreen,
        "main": MainScreen,
    }

    def __init__(
        self,
        db_path: Optional[str] = None,
        config: Optional[Path] = None,
    ):
        super().__init__(watch_css=True)
        self.dooit_mode: ModeType = "NORMAL"
        self.config = config
        manager.connect(db_path)

    async def base_setup(self):
        drop_blank_models()
        self.api = DooitAPI(self)
        self.api.plugin_manager.scan()
        self.post_message(Startup())
        self.post_message(ModeChanged("NORMAL"))
        self.push_screen("main")

    async def setup_poller(self):
        self.set_interval(1, self.poll_dooit_db)

    async def on_mount(self):
        await self.base_setup()
        await self.setup_poller()

    async def action_quit(self) -> None:
        drop_blank_models()
        self.post_message(ShutDown())
        return await super().action_quit()

    @property
    def project_tree(self) -> ProjectsTree:
        return self.screen.query_one(ProjectsTree)

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
            self.project_tree.refresh_options()
            todos_tree = self.api.vars.todos_tree
            if todos_tree:
                todos_tree.refresh_options()

    @on(QuitApp)
    async def quit_app(self):
        await self.action_quit()

    async def action_open_url(self, url: str) -> None:  # pragma: no cover
        # dooit's own opener rather than textual's: `App.open_url` goes
        # through `webbrowser`, which finds nothing at all under WSL - the
        # same reason the "o" key does not go through it either
        open_url(url)


if __name__ == "__main__":  # pragma: no cover
    Dooit().run()
