import click
from click.core import Context
from pathlib import Path

VERSION = "3.3.3"


def run_dooit(config_path_str: str | None, db_path_str: str | None):
    from dooit.ui.tui import Dooit
    from dooit.api._vars import DEFAULT_CONFIG_LOCATION, DATABASE_FILE

    config_path = Path(config_path_str or DEFAULT_CONFIG_LOCATION)
    db_path = Path(db_path_str or DATABASE_FILE)

    if not (config_path.exists() and config_path.is_file()):
        config_path.touch()
    if not (db_path.exists() and db_path.is_file()):
        db_path.touch()

    Dooit(config_path=config_path, db_path=db_path).run()


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.option(
    "--version",
    "-v",
    is_flag=True,
    help="Show version and exit.",
)
@click.option("-c", "--config", default=None, help="Path to config file")
@click.option("--db", default=None, help="Path to database file")
@click.pass_context
def main(ctx: Context, version: bool, config: str, db: str) -> None:
    if version:
        return print(f"dooit - {VERSION}")

    if ctx.invoked_subcommand is None:
        run_dooit(config_path_str=config, db_path_str=db)


@main.command(help="Show config location.")
def config_loc() -> None:
    """Print the location of the configuration file."""
    from dooit.api._vars import DEFAULT_CONFIG_LOCATION

    print(DEFAULT_CONFIG_LOCATION)


if __name__ == "__main__":
    main()
