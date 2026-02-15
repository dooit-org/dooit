from dooit.config.errors import ConfigError, ConfigValidationError
from dooit.config.utils import ConfigData


class ConfigValidator:
    """Validates merged config before application. Fail-fast on first error."""

    def __init__(self, config: ConfigData) -> None:
        self.config = config

    def validate(self) -> None:
        """Run all structural and cross-reference checks."""
        self._validate_general()
        self._validate_theme()
        self._validate_formatters()
        self._validate_scripts()
        self._validate_bar_widgets()
        self._validate_dashboard_widgets()

    def _validate_general(self) -> None:
        general = self.config.get("general")
        if not isinstance(general, dict):
            raise ConfigError("Missing [general] section in config")

        if "theme" not in general:
            raise ConfigError("Missing 'theme' key in [general] section")

    def _validate_theme(self) -> None:
        general = self.config["general"]
        theme_name = general["theme"]
        themes = self.config.get("theme", {})

        if theme_name not in themes:
            available = ", ".join(themes.keys()) if themes else "(none)"
            raise ConfigError(
                f"Theme '{theme_name}' not found. Available themes: {available}"
            )

    def _validate_formatters(self) -> None:
        formatter_config = self.config.get("formatter", {})

        if not isinstance(formatter_config, dict):
            raise ConfigValidationError(
                f"[formatter] must be a table, got {type(formatter_config).__name__}"
            )

        for model_type, fields in formatter_config.items():
            if not isinstance(fields, dict):
                raise ConfigValidationError(
                    f"[formatter.{model_type}] must be a table, "
                    f"got {type(fields).__name__}"
                )

            for field_name, field_config in fields.items():
                if not isinstance(field_config, dict):
                    raise ConfigValidationError(
                        f"[formatter.{model_type}.{field_name}] must be a table, "
                        f"got {type(field_config).__name__}"
                    )

    def _validate_scripts(self) -> None:
        scripts_config = self.config.get("script", {})

        if not isinstance(scripts_config, dict):
            raise ConfigValidationError(
                f"[script] must be a table, got {type(scripts_config).__name__}"
            )

        for name, script_config in scripts_config.items():
            if not isinstance(script_config, dict):
                raise ConfigValidationError(
                    f"[script.{name}] must be a table, "
                    f"got {type(script_config).__name__}"
                )

            if "_script" not in script_config:
                raise ConfigError(
                    f"[script.{name}] is missing a '_script' key. "
                    f"Every script section must reference a Python function "
                    f"via '_script = \"./path::function\"'."
                )

    def _validate_bar_widgets(self) -> None:
        bar_config = self.config.get("bar", {})
        widgets_left = bar_config.get("widgets_left", [])
        widgets_right = bar_config.get("widgets_right", [])

        for name in list(widgets_left) + list(widgets_right):
            self._require_script(name, "bar")

    def _validate_dashboard_widgets(self) -> None:
        dashboard_config = self.config.get("dashboard", {})
        widget_names = dashboard_config.get("widgets", [])

        for name in widget_names:
            self._require_script(name, "dashboard")

    def _require_script(self, name: str, section: str) -> None:
        """Assert that a script name is defined under [script.*]."""
        scripts_config = self.config.get("script", {})

        if name not in scripts_config:
            available = ", ".join(sorted(scripts_config.keys())) or "(none)"
            raise ConfigError(
                f"[{section}] references script '{name}', but no "
                f"[script.{name}] section exists. "
                f"Available scripts: {available}"
            )
