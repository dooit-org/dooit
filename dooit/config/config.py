import msgspec

from dooit.config.types import (
    BarConfig,
    DashboardConfig,
    FieldFormatter,
    FormatterConfig,
    GeneralConfig,
    KeysConfig,
    LayoutConfig,
    ScriptEntry,
    ThemeColors,
)


class AppConfig(msgspec.Struct, kw_only=True):
    general: GeneralConfig
    theme: dict[str, ThemeColors]
    layout: LayoutConfig
    keys: KeysConfig
    bar: BarConfig
    dashboard: DashboardConfig
    formatter: FormatterConfig
    script: dict[str, ScriptEntry]

    @classmethod
    def from_resolved(cls, data: dict) -> "AppConfig":
        def dec_hook(typ, obj):
            if typ is FieldFormatter:
                return FieldFormatter(obj)

            if typ is ScriptEntry:
                return ScriptEntry(obj)

            raise TypeError(f"Cannot convert {type(obj)} to {typ}")

        return msgspec.convert(data, cls, dec_hook=dec_hook)

    def get_active_theme(self) -> ThemeColors:
        return self.theme[self.general.theme]

    def get_scripts(self) -> dict:
        return self.script
