class ConfigError(Exception):
    """Raised when configuration is invalid or missing required values."""


class ConfigValidationError(ConfigError):
    """Raised when a config section has an unexpected type or structure."""
