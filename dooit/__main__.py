from typing import Optional
import click
from pathlib import Path
from platformdirs import user_data_dir, user_config_dir

OLD_CONFIG = Path(user_data_dir("dooit")) / "todo.yaml"
VERSION = "3.3.3"


def run_dooit(config: Optional[str] = None, db_path: Optional[str] = None):
    config_path = None if not config else Path(config)

    if config_path and not (config_path.exists() and config_path.is_file()):
        print(f"Config file {config} not found.")
        return

    from dooit.ui.tui import Dooit

    Dooit(config=config_path, db_path=db_path).run()


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
def main(ctx, version: bool, config: str, db: str) -> None:
    if version:
        return print(f"dooit - {VERSION}")

    if ctx.invoked_subcommand is None:
        if OLD_CONFIG.exists():
            from dooit.utils.cli_logger import logger

            logger.warn(
                "Found todos for v2.",
                "Please migrate to v3 using [reverse] dooit migrate [/reverse] first.",
            )
            return

        run_dooit(config=config, db_path=db)


@main.command(help="Migrate data from v2 to v3.")
def migrate() -> None:
    from dooit.utils.cli_logger import logger

    logger.info("Migrating from v2 ...")
    from dooit.backport.migrate_from_v2 import Migrator2to3

    migrator = Migrator2to3()
    migrator.migrate()


@main.command(help="Show config location.")
def config_loc() -> None:
    """Print the location of the configuration file."""
    print(Path(user_config_dir("dooit")) / "config.py")


if __name__ == "__main__":
    main()
