import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from yaml import safe_load
from pathlib import Path
from platformdirs import user_data_dir
from dooit.api import Todo, Workspace, manager
from dooit.utils.cli_logger import logger
from dooit.utils.database import delete_all_data

manager.connect()
BASE_PATH = Path(user_data_dir("dooit"))
operations = []


def parse_recurrence(recurrence: str) -> timedelta:
    """Parse a recurrence string (e.g., '2d', '1w') into a timedelta."""
    DURATION_LEGEND = {
        "m": "minute",
        "h": "hour",
        "d": "day",
        "w": "week",
    }

    def split_duration(duration: str) -> Tuple[str, str]:
        if re.match(r"^(\d+)[mhdw]$", duration):
            return duration[-1], duration[:-1]
        else:
            return tuple()

    sign, frequency = split_duration(recurrence)
    frequency = int(frequency)
    return timedelta(**{f"{DURATION_LEGEND[sign]}s": frequency})


def parse_due(due: str) -> Optional[datetime]:
    """Parse a due date string (timestamp or 'none') into a datetime or None."""
    if due == "none":
        return None

    due_float = float(due)
    return datetime.fromtimestamp(due_float)


class Migrator2to3:
    """
    Handles migration of data from dooit v2 (YAML-based) to v3 (SQLite-based).
    """

    old_location = BASE_PATH / "todo.yaml"
    new_location = BASE_PATH / "dooit.db"

    @classmethod
    def check_for_old_data(cls):
        """Check whether a v2 data file exists at the expected location."""
        if not cls.old_location.exists():
            return False

        return True

    def load_old(self):
        """Load and return the old v2 YAML configuration data."""
        with self.old_location.open() as f:
            return safe_load(f)

    def backup_old_config(self):
        """Rename the old v2 config file to a .bak backup."""
        logger.info("Moving old config to a backup file ...")

        backup_location = self.old_location.with_suffix(".bak")
        self.old_location.rename(backup_location)

        logger.success("Backup successful")

    def migrate(self):
        """Run the full migration from v2 YAML data to the v3 database."""
        logger.info("Checking for old data ...")

        if not self.check_for_old_data():
            logger.error("No old data found")
            return

        logger.info("Found old data. Converting ...")

        try:
            if self.new_location.exists():
                confirm = logger.console.input(
                    "Database already exists. Do you want to overwrite it? (y/n): "
                )
                if confirm.lower() == "y":
                    delete_all_data(manager.session)
                else:
                    logger.error("Migration aborted")
                    return

            data = self.load_old()
            for workspace in data:
                self.create_workspace(workspace)

            self.backup_old_config()
            logger.success("Successfully moved to new version. Happy todoing!")
        except Exception as e:
            logger.error(f"Error converting data: {e}")

    # ------------------------------------------------

    def create_workspace(self, data, parent=None):
        """Create a workspace and its children from v2 data recursively."""
        description = data.get("description")
        child_workspaces = data.get("workspaces", [])
        todos = data.get("todos", [])

        workspace = Workspace(description=description, parent_workspace=parent)
        workspace.save()

        for child in child_workspaces:
            self.create_workspace(child, parent=workspace)

        for child in todos:
            self.create_todo(child, parent_workspace=workspace)

    def create_todo(self, data: List, parent_todo=None, parent_workspace=None):
        """Create a todo and its children from v2 data recursively."""
        self_data = data[0]
        if len(data) == 1:
            children_data = []
        else:
            children_data = data[1]

        description = self_data.get("description")
        pending = self_data.get("status") != "COMPLETED"
        urgency = self_data.get("urgency")
        due = self_data.get("due")
        effort = self_data.get("effort")
        recurrence = self_data.get("recurrence")

        todo = Todo(
            parent_todo=parent_todo,
            parent_workspace=parent_workspace,
            description=description,
            pending=pending,
            urgency=urgency,
            due=parse_due(due),
            effort=int(effort) if effort else None,
            recurrence=parse_recurrence(recurrence) if recurrence else None,
        )
        todo.save()

        for data in children_data:
            self.create_todo(
                data,
                parent_todo=todo,
            )


if __name__ == "__main__":
    m = Migrator2to3()
    if m.check_for_old_data():
        m.migrate()
