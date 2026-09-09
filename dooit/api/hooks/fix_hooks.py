from sqlalchemy import event, text
from ..project import Project
from ..todo import Todo


@event.listens_for(Project, "before_insert")
def fix_order_id_project(_, connection, target: Project):
    if target.is_root:
        return

    if target.order_index is None or target.order_index == -1:
        target.order_index = len(target.siblings) - 1
        return

    if target.order_index >= 0:
        connection.execute(
            text("""
            UPDATE project
            SET order_index = order_index + 1
            WHERE order_index >= :current_index
            """),
            {"current_index": target.order_index, "target_id": target.id},
        )


@event.listens_for(Todo, "before_insert")
def fix_order_id_todo(_, connection, target: Todo):
    if target.order_index is None or target.order_index == -1:
        target.order_index = len(target.siblings) - 1

    if target.order_index >= 0:
        connection.execute(
            text("""
            UPDATE todo
            SET order_index = order_index + 1
            WHERE order_index >= :current_index
            """),
            {"current_index": target.order_index, "target_id": target.id},
        )
