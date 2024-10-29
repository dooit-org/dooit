<style>
h2 code {
    color: var(--vp-c-brand-1);
}
</style>

# Workspace

In this page, I'll lay out all the methods available on the workspace class

:::tip
As mentioned in the introduction, `Workspace` class is a table and any sql operations can be performed using sqlalchemy
:::

## `classmethod` from_id

```python
from_id(id: str | int) -> Workspace
```

Returns the workspace object with the given id

**Parameters:**

| Param|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| id            |                     | The id of the workspace object you want to get                                           |

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| Self          |                     | The workspace object                                                                     |

**Raises:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| ValueError    |                     | If an invalid ID is passed                                                               |


## `property` parent

```python
parent -> Workspace
```

Returns the parent of the workspace object

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| Workspace     |                     | The parent of the workspace object                                                       |

## `property` nest_level

```python
nest_level -> int
```

Returns the nested level from the root

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| int           |                     | Depth of the nesting                                                                     |


## `method` siblings

```python
siblings() -> List[Workspace]
```

Returns the siblings for the workspace (including self)

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

Adds a todo to the workspace object

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| Todo          |                     | The newly added todo                                                                     |


## `method` add_workspace

```python
add_workspace() -> Workspace
```

Adds a child workspace to the workspace object

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| Workspace     |                     | The newly added Workspace                                                                |



## `method` save


```python
save()
```

Saves any modifications done to the database

## `classmethod` all

```python
all() -> List[Workspace]
```

Returns all the workspaces from the database

**Returns:**

| Type|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| List[Self]    |                     | List of the workspaces present in the database                                           |