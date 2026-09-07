from sqlalchemy import event
from ..exceptions import NoParentError, MultipleParentError
from ..todo import Todo


@event.listens_for(Todo, "before_insert")
@event.listens_for(Todo, "before_update")
def validate_parent_todo(mapper, connection, target: Todo):
    if target.parent_project is None and target.parent_todo is None:
        # Unless it outlived the project it was filed under: a todo that was
        # thrown away, or finished, keeps the path it came from in place of a
        # parent, and is put back into that project when it is revived
        if not target.origin_path:
            raise NoParentError("Todo must have a parent project or todo")

    if target.parent_project is not None and target.parent_todo is not None:
        raise MultipleParentError("Todo cannot have both a parent project and todo")


@event.listens_for(Todo, "before_insert")
@event.listens_for(Todo, "before_update")
def validate_priority(mapper, connection, target: Todo):
    if target.priority is None:
        return

    # 0 means "no priority", 1 is the highest and 3 the lowest
    target.priority = max(0, target.priority)
    target.priority = min(3, target.priority)
