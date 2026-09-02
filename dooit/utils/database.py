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


def delete_all_data(session: Session):
    meta = MetaData()
    meta.reflect(bind=session.get_bind())
    for table in reversed(meta.sorted_tables):
        session.execute(table.delete())
    session.commit()
