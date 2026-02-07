from pathlib import Path
from string import Template
from .data import ConfigData

from .script_parser import ScriptParser


class ConfigResolver:
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
