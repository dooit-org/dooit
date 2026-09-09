<style>
h2 code {
    color: var(--vp-c-brand-1);
}
</style>

# Project

In this page, I'll lay out all the methods available on the project class

:::tip :bulb: TIP
As mentioned in the introduction, `Project` class is a table and any sql operations can be performed using sqlalchemy
:::

<!-- ----------------------- ATTRIBUTES ---------------------------------- -->

## `attr`  description

The description of the project

```python
description: Mapped[str] = mapped_column(default="")
```

## `attr`  parent_project

The parent project of the workpsace

```python
parent_project: Mapped[Optional["Project"]] = relationship(
    "Project",
    back_populates="projects",
    remote_side=[id],
)
```

## `attr`  projects

The child projects of the project

```python
projects: Mapped[List["Project"]] = relationship(
    "Project",
    back_populates="parent_project",
    cascade="all",
    order_by="Project.order_index",
)
```

## `attr` todos

The todos for the project

```python
todos: Mapped[List["Todo"]] = relationship(
    "Todo",
    back_populates="parent_project",
    cascade="all, delete-orphan",
    order_by="Todo.order_index",
)
```

<!-- --------------------- CLASSMETHODS ----------------------------------- -->

## `classmethod` from_id

```python
from_id(id: str | int) -> Project
```

Returns the project object with the given id

**Parameters:**

| Param|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| id            |                     | The id of the project object you want to get                                           |

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| Self          |                     | The project object                                                                     |

**Raises:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| ValueError    |                     | If an invalid ID is passed                                                               |


## `classmethod` all

```python
all() -> List[Project]
```

Returns all the projects from the database

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| List[Self]    |                     | List of the projects present in the database                                           |

<!-- ---------------- PROPERTIES ------------------------------------- -->

## `property` parent

```python
parent -> Project
```

Returns the parent of the project object

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| Project     |                     | The parent of the project object                                                       |

## `property` nest_level

```python
nest_level -> int
```

Returns the nested level from the root

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| int           |                     | Depth of the nesting                                                                     |


<!-- ------------------ METHODS -------------------------------------- -->

## `method` siblings

```python
siblings() -> List[Project]
```

Returns the siblings for the project (including self)

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| List[Self]    |                     | List of the siblings (including self)                                                    |


## `method` sort_siblings


```python
sort_siblings()
```

Sorts all the siblings ***(by description)***


## `method` add_todo

```python
add_todo() -> Todo
```

Adds a todo to the project object

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| Todo          |                     | The newly added todo                                                                     |


## `method` add_project

```python
add_project() -> Project
```

Adds a child project to the project object

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| Project     |                     | The newly added Project                                                                |

## `method` shift_down

Shifts the project down by one index (Nothing happens if its the first project)

```python
shift_down()
```

## `method` shift_up

Shifts the project down by one index (Nothing happens if its the last project)

```python
shift_up()
```

## `method` save

Saves any modifications done on the attributes to the database

```python
save()
```

