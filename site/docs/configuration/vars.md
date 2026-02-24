<style>
h2 code {
    color: var(--vp-c-brand-1);
}
</style>

# Dooit Vars

This api component exposes some of the stuff running on dooit + act as a global register to tweak settings \
Its still developing and I'll add more stuff to it as per demand!

## `editable` always_expand_workspaces

If set to `True`, the workspaces will always be expanded

```py
def always_expand_workspaces(self) -> bool
```

## `editable` always_expand_todos

If set to `True`, the todos will always be expanded

```py
def always_expand_todos(self) -> bool
```


## `editable` show_confirm

Returns a boolean value if confirmation is enabled

```py
def show_confirm(self) -> bool
```

Returns the current mode of the app (`NORMAL/INSERT/SORT/CONFIRM/DATE/SEARCH`)

```py{6}
from dooit.ui.bridge.events import DooitEvent
from dooit.ui.bridge import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    api.vars.show_confirm = False # disables confirmation check
```

## `readonly` mode

```py
def mode(self) -> str
```

Returns the current mode of the app (`NORMAL/INSERT/SORT/CONFIRM/DATE/SEARCH`)

```py{6}
from dooit.ui.bridge.events import DooitEvent
from dooit.ui.bridge import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    mode = api.vars.mode
```
## `readonly` theme

```py
def theme(self) -> DooitThemeBase
```

Returns the current theme object (see [theme](../configuration/theme.md))

```py{6}
from dooit.ui.bridge.events import DooitEvent
from dooit.ui.bridge import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    theme = api.vars.theme
```

---

## `readonly` workspaces_tree

```py
def workspaces_tree(self) -> WorkspacesTree
```

Returns the current workspaces tree object

```py{6}
from dooit.ui.bridge.events import DooitEvent
from dooit.ui.bridge import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    workspaces_tree = api.vars.workspaces_tree
```

---

## `readonly` current_workspace

```py
def current_workspace(self) -> Optional[Workspace]
```

Returns the currently highlighted workspace object if available; otherwise, returns `None` (see [workspace](../backend/workspace.md))

```py{6}
from dooit.ui.bridge.events import DooitEvent
from dooit.ui.bridge import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    current_workspace = api.vars.current_workspace
```

---

## `readonly` todos_tree

```py
def todos_tree(self) -> Optional[TodosTree]
```

Returns the todos tree for the current workspace if available; otherwise, returns `None`

```py{6}
from dooit.ui.bridge.events import DooitEvent
from dooit.ui.bridge import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    todos_tree = api.vars.todos_tree
```

---

## `readonly` current_todo

```py
def current_todo(self) -> Optional[Todo]
```

Returns the currently highlighted todo item if available; otherwise, returns `None` (see [todo](../backend/todo.md))

```py{6}
from dooit.ui.bridge.events import DooitEvent
from dooit.ui.bridge import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    current_todo = api.vars.current_todo
```
