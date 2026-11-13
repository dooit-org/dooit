from typing import Any, Optional
from sqlalchemy import event, text
from ..workspace import Workspace
from ..todo import Todo


def parent_id(parent: Any, fallback: Optional[int]) -> Optional[int]:
    # the foreign key is not always filled in yet when inserting
    return parent.id if parent is not None else fallback


@event.listens_for(Workspace, "before_insert")
def fix_order_id_workspace(_, connection, target: Workspace):
    if target.is_root:
        return

    if target.order_index is None or target.order_index == -1:
        target.order_index = len(target.siblings) - 1
        return

    if target.order_index >= 0:
        connection.execute(
            text("""
            UPDATE workspace
            SET order_index = order_index + 1
            WHERE order_index >= :current_index
            AND parent_workspace_id IS :parent_workspace_id
            """),
            {
                "current_index": target.order_index,
                "parent_workspace_id": parent_id(
                    target.parent_workspace, target.parent_workspace_id
                ),
            },
        )


@event.listens_for(Todo, "before_insert")
def fix_order_id_todo(_, connection, target: Todo):
    if target.order_index is None or target.order_index == -1:
        target.order_index = len(target.siblings) - 1
        return

    if target.order_index >= 0:
        connection.execute(
            text("""
            UPDATE todo
            SET order_index = order_index + 1
            WHERE order_index >= :current_index
            AND parent_workspace_id IS :parent_workspace_id
            AND parent_todo_id IS :parent_todo_id
            """),
            {
                "current_index": target.order_index,
                "parent_workspace_id": parent_id(
                    target.parent_workspace, target.parent_workspace_id
                ),
                "parent_todo_id": parent_id(target.parent_todo, target.parent_todo_id),
            },
        )
