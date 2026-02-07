from pathlib import Path

from dooit.config.utils import ConfigData, ConfigResolver
from dooit.config.utils.script_reader import ScriptReader, ScriptFunction
from dooit.config.utils.script_parser import ScriptReaderFactory
from dooit.config.utils.script_parser import (
    ScriptParser,
    RefreshConfig,
    RefreshKind,
)
from dooit.config.service import ConfigService
from dooit.ui.api.api_components.formatters._decorators import MUTLIPLE_FORMATTER_ATTR
from dooit.ui.api.events import ModeChanged
from dooit.ui.tui import Dooit
from tests.test_ui.ui_base import run_pilot


def _write_script(path: Path, content: str) -> None:
    path.write_text(content)


async def test_script_function_call_filters_system_params(tmp_path: Path):
    script_path = tmp_path / "scripts.py"
    _write_script(
        script_path,
        "\n".join(
            [
                "def foo(**kwargs):",
                "    return kwargs",
                "",
                "def bar(event, **kwargs):",
                "    return event.mode",
            ]
        ),
    )

    reader = ScriptReader(script_path)
    script_func = reader.get_function("foo")
    assert script_func.call(_hidden="skip", value=1) == {"value": 1}

    event_func = reader.get_function("bar")
    event = ModeChanged("NORMAL")
    assert event_func.call(event=event, _hidden="skip") == "NORMAL"


async def test_script_reader_factory_caches_readers(tmp_path: Path):
    script_path = tmp_path / "scripts.py"
    _write_script(script_path, "def main(): return 'test'")

    reader1 = ScriptReaderFactory.get_reader(script_path)
    reader2 = ScriptReaderFactory.get_reader(script_path)
    assert reader1 is reader2


def test_parse_refresh_interval_seconds():
    assert ScriptParser.parse_refresh_interval("every 5s") == 5
    assert ScriptParser.parse_refresh_interval("every 30s") == 30


def test_parse_refresh_interval_minutes():
    assert ScriptParser.parse_refresh_interval("every 5m") == 300
    assert ScriptParser.parse_refresh_interval("every 1m") == 60


def test_parse_refresh_interval_hours():
    assert ScriptParser.parse_refresh_interval("every 2h") == 7200
    assert ScriptParser.parse_refresh_interval("every 1h") == 3600


def test_parse_refresh_interval_invalid():
    assert ScriptParser.parse_refresh_interval("invalid") is None
    assert ScriptParser.parse_refresh_interval("every") is None
    assert ScriptParser.parse_refresh_interval("every 5x") is None


def test_parse_event_valid():
    event_cls = ScriptParser.parse_event("on ModeChanged")
    assert event_cls is ModeChanged


def test_parse_event_invalid():
    assert ScriptParser.parse_event("on NonExistentEvent") is None
    assert ScriptParser.parse_event("on") is None
    assert ScriptParser.parse_event("on ") is None


def test_parse_reload_targets_single():
    result = ScriptParser.parse_reload_targets("bar")
    assert result == {"bar"}


def test_parse_reload_targets_multiple():
    result = ScriptParser.parse_reload_targets("bar, dashboard, todos")
    assert result == {"bar", "dashboard", "todos"}


def test_parse_reload_targets_empty():
    assert ScriptParser.parse_reload_targets(None) == set()
    assert ScriptParser.parse_reload_targets("") == set()


def test_parse_reload_targets_whitespace():
    result = ScriptParser.parse_reload_targets("  bar  ,  dashboard  ")
    assert result == {"bar", "dashboard"}


def test_resolve_script_refresh_interval(tmp_path: Path):
    script_path = tmp_path / "scripts.py"
    _write_script(script_path, "def foo(): return 'ok'")

    config_path = tmp_path / "config.toml"
    config = ConfigData.from_dict(
        {
            "formatter": {
                "todo": {
                    "status": {
                        "_script": "./scripts.py::foo",
                        "_refresh": "every 5s",
                    }
                }
            }
        }
    )

    resolved = ConfigResolver.resolve_script_funcs(config_path, config)
    entry = resolved["formatter"]["todo"]["status"]["_script"]
    assert isinstance(entry.refresh, RefreshConfig)
    assert entry.refresh.kind is RefreshKind.INTERVAL
    assert entry.refresh.value == 5


def test_resolve_script_refresh_event(tmp_path: Path):
    script_path = tmp_path / "scripts.py"
    _write_script(script_path, "def foo(): return 'ok'")

    config_path = tmp_path / "config.toml"
    config = ConfigData.from_dict(
        {
            "formatter": {
                "todo": {
                    "status": {
                        "_script": "./scripts.py::foo",
                        "_refresh": "on ModeChanged",
                    }
                }
            }
        }
    )

    resolved = ConfigResolver.resolve_script_funcs(config_path, config)
    entry = resolved["formatter"]["todo"]["status"]["_script"]
    assert isinstance(entry.refresh, RefreshConfig)
    assert entry.refresh.kind is RefreshKind.EVENT
    assert entry.refresh.value is ModeChanged


async def test_apply_formatters_clear_true(tmp_path: Path):
    script_path = tmp_path / "formatters.py"
    _write_script(
        script_path,
        "\n".join(
            [
                "def status_override(model, **kwargs):",
                "    return 'override'",
            ]
        ),
    )

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[formatter.todo.status]",
                '_script = "./formatters.py::status_override"',
                "_clear = true",
            ]
        )
    )

    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        service = ConfigService(app.api, config_path)

        store = app.api.formatter.todos.status
        store.add(lambda value, model: "existing", id="existing")

        service._apply_formatters()

        assert "existing" not in store.formatters
        assert "config_todo_status" in store.formatters


async def test_apply_formatters_clear_false(tmp_path: Path):
    script_path = tmp_path / "formatters.py"
    _write_script(
        script_path,
        "\n".join(
            [
                "def status_enhance(formatted_text, model, **kwargs):",
                "    return formatted_text",
            ]
        ),
    )

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[formatter.todo.status]",
                '_script = "./formatters.py::status_enhance"',
                "_clear = false",
            ]
        )
    )

    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        service = ConfigService(app.api, config_path)

        store = app.api.formatter.todos.status
        store.add(lambda value, model: "existing", id="existing")

        service._apply_formatters()

        assert "existing" in store.formatters
        config_formatter = store.formatters.get("config_todo_status")
        assert config_formatter is not None
        assert hasattr(config_formatter.func, MUTLIPLE_FORMATTER_ATTR)
