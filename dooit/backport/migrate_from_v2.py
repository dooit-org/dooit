import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from yaml import safe_load
from pathlib import Path
from platformdirs import user_data_dir
from dooit.api import Todo, Project, manager
from dooit.utils.cli_logger import logger
from dooit.utils.database import delete_all_data, urgency_to_priority

manager.connect()
BASE_PATH = Path(user_data_dir("dooit"))
operations = []


def parse_recurrence(recurrence: str) -> timedelta:
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
    if due == "none":
        return None

    due_float = float(due)
    return datetime.fromtimestamp(due_float)


class Migrator2to3:
    old_location = BASE_PATH / "todo.yaml"
    new_location = BASE_PATH / "dooit.db"

    @classmethod
    def check_for_old_data(cls):
        if not cls.old_location.exists():
            return False

        return True

    def load_old(self):
        with self.old_location.open() as f:
            return safe_load(f)

    def backup_old_config(self):
        logger.info("Moving old config to a backup file ...")

        backup_location = self.old_location.with_suffix(".bak")
        self.old_location.rename(backup_location)

        logger.success("Backup successful")

    def migrate(self):
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
            for project in data:
                self.create_project(project)

            self.backup_old_config()
            logger.success("Successfully moved to new version. Happy todoing!")
        except Exception as e:
            logger.error(f"Error converting data: {e}")

    # ------------------------------------------------

    def create_project(self, data, parent=None):
        description = data.get("description")
        # v2 called projects "workspaces", and that is the key still sitting in
        # the old yaml file on disk
        child_projects = data.get("workspaces", [])
        todos = data.get("todos", [])

        project = Project(description=description, parent_project=parent)
        project.save()

        for child in child_projects:
            self.create_project(child, parent=project)

        for child in todos:
            self.create_todo(child, parent_project=project)

    def create_todo(self, data: List, parent_todo=None, parent_project=None):
        self_data = data[0]
        if len(data) == 1:
            children_data = []
        else:
            children_data = data[1]

        description = self_data.get("description")
        pending = self_data.get("status") != "COMPLETED"
        urgency = self_data.get("urgency")
        priority = urgency_to_priority(int(urgency) if urgency else None)
        due = self_data.get("due")
        effort = self_data.get("effort")
        recurrence = self_data.get("recurrence")

        todo = Todo(
            parent_todo=parent_todo,
            parent_project=parent_project,
            description=description,
            pending=pending,
            priority=priority,
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
