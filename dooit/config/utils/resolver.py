from pathlib import Path
from string import Template
from .data import ConfigData

from .script_parser import ScriptParser, ScriptEntry
from .formatter_parser import FormatterParser


class ConfigResolver:
    @classmethod
    def resolve(cls, path: Path | str, config: ConfigData) -> ConfigData:
        """Run the full resolution pipeline: vars -> reload_targets -> scripts -> formatters."""
        config = cls.resolve_vars(config)
        config = cls.resolve_reload_targets(config)
        config = cls.resolve_script_funcs(path, config)
        config = cls.resolve_formatters(config)
        return config

    @classmethod
    def resolve_reload_targets(cls, config: ConfigData) -> ConfigData:
        """Inject reload_targets for scripts referenced by bar and dashboard."""
        scripts = config.get("script", {})
        if not isinstance(scripts, dict):
            return config

        target_map = {
            "bar": (
                list(config.get("bar", {}).get("widgets_left", []))
                + list(config.get("bar", {}).get("widgets_right", []))
            ),
            "dashboard": list(config.get("dashboard", {}).get("widgets", [])),
        }

        for target_name, script_names in target_map.items():
            for name in script_names:
                if name not in scripts or not isinstance(scripts[name], dict):
                    continue
                existing = scripts[name].get("reload_targets", [])
                if isinstance(existing, (list, tuple, set)):
                    existing = list(existing)
                else:
                    existing = []
                if target_name not in existing:
                    existing.append(target_name)
                scripts[name]["reload_targets"] = existing

        return config

    @classmethod
    def resolve_vars(cls, config: ConfigData) -> ConfigData:
        config_vars = config.get("vars", {})
        assert isinstance(config_vars, dict)

        def resolve(config: ConfigData) -> ConfigData:
            new_config = ConfigData()
            for key, value in config.items():
                if isinstance(value, str):
                    template = Template(value)
                    new_config[key] = template.substitute(config_vars)
                elif isinstance(value, dict):
                    new_config[key] = resolve(value)
                else:
                    new_config[key] = value
            return new_config

        return resolve(config)

    @classmethod
    def resolve_script_funcs(
        cls, path: Path | str, config_data: ConfigData
    ) -> ConfigData:
        """
        Recursively resolve _script references in config_data, returning a new ConfigData object.
        Replaces string references with ScriptEntry objects.
        """
        path = Path(path)
        new_config = ConfigData()
        for key, value in config_data.items():
            if key == "_script" and isinstance(value, str):
                new_config[key] = ScriptParser.parse_script_entry(
                    path, value, config_data
                )
            elif isinstance(value, dict):
                new_config[key] = cls.resolve_script_funcs(path, value)
            else:
                new_config[key] = value
        return new_config

    @classmethod
    def resolve_formatters(cls, config_data: ConfigData) -> ConfigData:
        """
        Resolve formatter sections: replace ScriptEntry with FormatterEntry
        for each field under [formatter.<model_type>.<field_name>].
        """
        formatter_config = config_data.get("formatter")
        if not isinstance(formatter_config, dict):
            return config_data

        new_formatter = ConfigData()
        for model_type, fields in formatter_config.items():
            if not isinstance(fields, dict):
                new_formatter[model_type] = fields
                continue

            new_fields = ConfigData()
            for field_name, field_config in fields.items():
                if not isinstance(field_config, dict):
                    new_fields[field_name] = field_config
                    continue

                script_entry = field_config.get("_script")
                if isinstance(script_entry, ScriptEntry):
                    new_field = ConfigData()
                    for k, v in field_config.items():
                        new_field[k] = v
                    new_field["_script"] = FormatterParser.parse(
                        script_entry.func, field_config, model_type
                    )
                    new_fields[field_name] = new_field
                else:
                    new_fields[field_name] = field_config

            new_formatter[model_type] = new_fields

        new_config_data = ConfigData()
        for k, v in config_data.items():
            new_config_data[k] = v
        new_config_data["formatter"] = new_formatter
        return new_config_data
