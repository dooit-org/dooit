from typing import Optional
from sqlalchemy import Engine, MetaData, inspect, text
from sqlalchemy.orm import Session


# Todos used to carry an "urgency" from 1 (lowest, and the default) up to 4
# (highest). Priority runs the other way around: 1 is the highest and 3 the
# lowest, with 0 meaning "no priority set".
URGENCY_TO_PRIORITY = {1: 0, 2: 3, 3: 2, 4: 1}


def urgency_to_priority(urgency: Optional[int]) -> int:
    if urgency is None:
        return 0

    return URGENCY_TO_PRIORITY.get(urgency, 0)


def migrate_urgency_to_priority(engine: Engine):
    """
    Rename a legacy `urgency` column to `priority` and flip its values over to
    the new scale. Does nothing once the database has been migrated.
    """

    inspector = inspect(engine)
    if "todo" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("todo")}
    if "urgency" not in columns or "priority" in columns:
        return

    # a single statement, so that remapped values can't collide with the
    # not-yet-remapped ones
    cases = " ".join(
        f"WHEN {urgency} THEN {priority}"
        for urgency, priority in URGENCY_TO_PRIORITY.items()
    )

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE todo RENAME COLUMN urgency TO priority"))
        connection.execute(
            text(f"UPDATE todo SET priority = CASE priority {cases} ELSE 0 END")
        )


def rename_workspace_to_project(engine: Engine):
    """
    Rename a legacy `workspace` table to `project`, along with the
    `parent_workspace_id` columns that point at it.

    Without this `create_all` would find no `project` table, happily create an
    empty one next to the old one, and leave every existing project and its
    todos stranded in a table nothing reads any more.
    """

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "workspace" not in tables or "project" in tables:
        return

    def has_column(table: str, column: str) -> bool:
        return any(col["name"] == column for col in inspector.get_columns(table))

    statements = ["ALTER TABLE workspace RENAME TO project"]

    # Renaming the table is enough for sqlite to repoint the foreign keys that
    # referenced it; the columns holding them still have to be renamed by hand.
    if has_column("workspace", "parent_workspace_id"):
        statements.append(
            "ALTER TABLE project RENAME COLUMN parent_workspace_id TO parent_project_id"
        )

    if "todo" in tables and has_column("todo", "parent_workspace_id"):
        statements.append(
            "ALTER TABLE todo RENAME COLUMN parent_workspace_id TO parent_project_id"
        )

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def add_scheduled_column(engine: Engine):
    """
    Add the `scheduled` column to a todo table written before it existed.

    `create_all` only ever creates whole tables that are missing, so a database
    from an older version keeps its todo table exactly as it was.
    """

    inspector = inspect(engine)
    if "todo" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("todo")}
    if "scheduled" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE todo ADD COLUMN scheduled DATETIME"))


def add_note_column(engine: Engine):
    """
    Add the `note` column to a todo table written before it existed.

    Same story as `add_scheduled_column`: `create_all` never touches a table it
    already found, so the column has to be bolted on by hand.
    """

    inspector = inspect(engine)
    if "todo" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("todo")}
    if "note" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE todo ADD COLUMN note TEXT NOT NULL DEFAULT ''")
        )


def add_completed_at_column(engine: Engine):
    """
    Add the `completed_at` column to a todo table written before it existed.

    Same story as `add_scheduled_column`. Todos completed before there was
    anywhere to write the date keep an empty one: the Completed project sorts
    them below everything that carries a real date.
    """

    inspector = inspect(engine)
    if "todo" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("todo")}
    if "completed_at" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE todo ADD COLUMN completed_at DATETIME"))


def add_bin_columns(engine: Engine):
    """
    Add the columns the Bin is kept in to a todo table written before it
    existed.

    Same story as `add_scheduled_column`. Nothing that was already in the
    database was ever thrown away, so every existing row starts out with an
    empty bin date and no path of its own to remember.
    """

    inspector = inspect(engine)
    if "todo" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("todo")}

    statements = []

    if "binned_at" not in columns:
        statements.append("ALTER TABLE todo ADD COLUMN binned_at DATETIME")

    if "origin_path" not in columns:
        statements.append(
            "ALTER TABLE todo ADD COLUMN origin_path TEXT NOT NULL DEFAULT ''"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def delete_all_data(session: Session):
    meta = MetaData()
    meta.reflect(bind=session.get_bind())
    for table in reversed(meta.sorted_tables):
        session.execute(table.delete())
    session.commit()
