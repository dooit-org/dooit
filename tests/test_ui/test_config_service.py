from pathlib import Path

from dooit.config.service import ConfigService
from dooit.config.utils import NestedDict, ConfigResolver
from dooit.config.utils.formatter_parser import (
    FormatterEntry,
    FormatterParser,
)
from dooit.config.utils.script_parser import (
    RefreshConfig,
    RefreshKind,
    ScriptParser,
    ScriptReaderFactory,
)
from dooit.config.utils.script_reader import ScriptReader
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
    config = NestedDict.from_dict(
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

    resolved = ConfigResolver.resolve_script_paths(config_path, config)
    entry = resolved["formatter"]["todo"]["status"]["_script"]
    assert isinstance(entry.refresh, RefreshConfig)
    assert entry.refresh.kind is RefreshKind.INTERVAL
    assert entry.refresh.value == 5


def test_resolve_script_refresh_event(tmp_path: Path):
    script_path = tmp_path / "scripts.py"
    _write_script(script_path, "def foo(): return 'ok'")

    config_path = tmp_path / "config.toml"
    config = NestedDict.from_dict(
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

    resolved = ConfigResolver.resolve_script_paths(config_path, config)
    entry = resolved["formatter"]["todo"]["status"]["_script"]
    assert isinstance(entry.refresh, RefreshConfig)
    assert entry.refresh.kind is RefreshKind.EVENT
    assert entry.refresh.value is ModeChanged


def test_resolve_formatters_produces_formatter_entry(tmp_path: Path):
    script_path = tmp_path / "scripts.py"
    _write_script(script_path, "def fmt(todo): return 'ok'")

    config_path = tmp_path / "config.toml"
    config = NestedDict.from_dict(
        {
            "formatter": {
                "todo": {
                    "status": {
                        "_script": "./scripts.py::fmt",
                    }
                }
            }
        }
    )

    resolved = ConfigResolver.resolve_script_paths(config_path, config)
    resolved = ConfigResolver.resolve_formatters(resolved)

    entry = resolved["formatter"]["todo"]["status"]["_script"]
    assert isinstance(entry, FormatterEntry)


def test_resolve_formatters_skips_non_formatter_sections(tmp_path: Path):
    config = NestedDict.from_dict(
        {"general": {"theme": "default"}, "keys": {"action": "ctrl+a"}}
    )

    resolved = ConfigResolver.resolve_formatters(config)
    assert resolved["general"]["theme"] == "default"
    assert resolved["keys"]["action"] == "ctrl+a"


async def test_apply_formatters_sets_func(tmp_path: Path):
    script_path = tmp_path / "formatters.py"
    _write_script(
        script_path,
        "\n".join(
            [
                "def status_fmt(model, **kwargs):",
                "    return 'formatted'",
            ]
        ),
    )

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[formatter.todo.status]",
                '_script = "./formatters.py::status_fmt"',
            ]
        )
    )

    async with run_pilot() as pilot:
        app = pilot.app
        assert isinstance(app, Dooit)
        service = ConfigService(app.api, config_path)

        store = app.api.formatter.todos.status
        service._apply_formatters()

        assert store.func is not None


async def test_formatter_parser_produces_entry(tmp_path: Path):
    script_path = tmp_path / "fmt.py"
    _write_script(
        script_path,
        "def render(todo, **kwargs): return 'overridden'",
    )

    reader = ScriptReader(script_path)
    script_func = reader.get_function("render")

    field_config = {"_script": script_func}
    entry = FormatterParser.parse(script_func, field_config, "todo")

    assert isinstance(entry, FormatterEntry)


async def test_formatter_parser_calls_script(tmp_path: Path):
    script_path = tmp_path / "fmt.py"
    _write_script(script_path, "def render(todo, color='red'): return color")

    reader = ScriptReader(script_path)
    script_func = reader.get_function("render")

    field_config = {"_script": script_func, "color": "blue"}
    entry = FormatterParser.parse(script_func, field_config, "todo")

    result = entry.func("mock_model")
    assert result == "blue"


async def test_formatter_parser_filters_internal_keys(tmp_path: Path):
    script_path = tmp_path / "fmt.py"
    _write_script(script_path, "def render(todo, **kwargs): return kwargs")

    reader = ScriptReader(script_path)
    script_func = reader.get_function("render")

    field_config = {
        "_script": script_func,
        "_clear": True,
        "_refresh": "every 5s",
        "color": "green",
        "size": 12,
    }
    entry = FormatterParser.parse(script_func, field_config, "todo")

    result = entry.func("mock_model")
    assert result == {"color": "green", "size": 12}
