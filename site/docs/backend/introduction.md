# Introduction

Dooit uses [sqlalchemy](https://www.sqlalchemy.org/) to store its data

For backend, **there are two tables**: `Workspace` and  `Todo`

You can easily import them from `dooit.api`

```py
from dooit.models import Workspace, Todo, manager
manager.connect() # this sets up connection to the database

# from here on, you can perform any operations
```

An overview code below will show you the relationship between these two models

## Workspace

```python
class Workspace(DooitModel):
    parent_workspace_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workspace.id"), default=None
    )
    parent_workspace: Mapped[Optional["Workspace"]] = relationship(
        "Workspace",
        back_populates="workspaces",
        remote_side=[id],
    )

    workspaces: Mapped[List["Workspace"]] = relationship(
        "Workspace",
        back_populates="parent_workspace",
        cascade="all",
        order_by="Workspace.order_index",
    )
    todos: Mapped[List["Todo"]] = relationship(
        "Todo",
        back_populates="parent_workspace",
        cascade="all, delete-orphan",
        order_by="Todo.order_index",
    )
```

## Todo

```python

class Todo(DooitModel):
    parent_workspace_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workspace.id")
    )
    parent_workspace: Mapped[Optional["Workspace"]] = relationship(
        "Workspace",
        back_populates="todos",
    )
    parent_todo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("todo.id"))

    parent_todo: Mapped[Optional["Todo"]] = relationship(
        "Todo",
        back_populates="todos",
        remote_side=[id],
    )

    todos: Mapped[List["Todo"]] = relationship(
        "Todo",
        back_populates="parent_todo",
        cascade="all, delete-orphan",
        order_by=order_index,
    )


```
