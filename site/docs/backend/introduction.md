# Introduction

Dooit uses [sqlalchemy](https://www.sqlalchemy.org/) to store its data

For backend, **there are two tables**: `Project` and  `Todo`

You can easily import them from `dooit.api`

```py
from dooit.api import Project, Todo, manager
manager.connect() # this sets up connection to the database

# from here on, you can perform any operations
```

An overview code below will show you the relationship between these two models

## Project

```python
class Project(DooitModel):
    parent_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("project.id"), default=None
    )
    parent_project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="projects",
        remote_side=[id],
    )

    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="parent_project",
        cascade="all",
        order_by="Project.order_index",
    )
    todos: Mapped[List["Todo"]] = relationship(
        "Todo",
        back_populates="parent_project",
        cascade="all, delete-orphan",
        order_by="Todo.order_index",
    )
```

## Todo

```python

class Todo(DooitModel):
    parent_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("project.id")
    )
    parent_project: Mapped[Optional["Project"]] = relationship(
        "Project",
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

