from sqlalchemy import event
from ..exceptions import NoParentError, MultipleParentError
from ..todo import Todo


@event.listens_for(Todo, "before_insert")
@event.listens_for(Todo, "before_update")
def validate_parent_todo(mapper, connection, target: Todo):
    if target.parent_workspace is None and target.parent_todo is None:
        raise NoParentError("Todo must have a parent workspace or todo")

    if target.parent_workspace is not None and target.parent_todo is not None:
        raise MultipleParentError("Todo cannot have both a parent workspace and todo")


@event.listens_for(Todo, "before_insert")
@event.listens_for(Todo, "before_update")
def validate_urgency(mapper, connection, target: Todo):
    if target.urgency is None:
        return

    target.urgency = max(1, target.urgency)
    target.urgency = min(4, target.urgency)
