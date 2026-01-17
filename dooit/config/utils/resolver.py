from pathlib import Path
from string import Template

from .data import ConfigData
from .script_reader import ScriptReader


class ScriptReaderFactory:
    """
    Factory for ScriptReader instances with caching.

    Methods
    -------
    get_reader(path: Path) -> ScriptReader
        Returns a ScriptReader for the given path, using a cache
        to avoid re-loading modules unnecessarily.

    Notes
    -----
    The _cache attribute stores ScriptReader instances keyed by the
    resolved absolute file path. This ensures each config or script
    file is loaded only once per process.
    """

    _cache = {}

    @classmethod
    def get_reader(cls, path: Path) -> ScriptReader:
        resolved_path = path.resolve()
        if resolved_path not in cls._cache:
            cls._cache[resolved_path] = ScriptReader(resolved_path)
        return cls._cache[resolved_path]


class ConfigResolver:
    """
    This class takes a config data and resolves vars
    which makes everything absolute for service to read
    """

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
        Replaces string references with ScriptFunction objects.
        """
        path = Path(path)
        new_config = ConfigData()
        for key, value in config_data.items():
            if key == "_script" and isinstance(value, str):
                if "::" not in value:
                    raise ValueError(f"Invalid script reference: {value}")

                script_path_str, func = value.split("::", 1)
                script_path = Path(script_path_str)
                if not script_path.is_absolute():
                    script_path = (path.parent / script_path).resolve()

                if script_path.suffix == "":
                    candidate = script_path.with_suffix(".py")
                    if candidate.exists():
                        script_path = candidate

                reader = ScriptReaderFactory.get_reader(script_path)
                new_config[key] = reader.get_function(func.strip())
            elif isinstance(value, dict):
                new_config[key] = cls.resolve_script_funcs(path, value)
            else:
                new_config[key] = value
        return new_config
