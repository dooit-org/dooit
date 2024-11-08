# Dooit Vars

This api component exposes some of the stuff running on dooit + act as a global register to tweak settings \
Its still developing and I'll add more stuff to it as per demand!

## theme

```py
def theme(self) -> DooitThemeBase
```

Returns the current theme object (see [theme](../configuration/theme.md))

```py{6}
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    theme = api.vars.theme
```

---

## workspaces_tree

```py
def workspaces_tree(self) -> WorkspacesTree
```

Returns the current workspaces tree object

```py{6}
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    workspaces_tree = api.vars.workspaces_tree
```

---

## current_workspace

```py
def current_workspace(self) -> Optional[Workspace]
```

Returns the currently highlighted workspace object if available; otherwise, returns `None` (see [workspace](../backend/workspace.md))

```py{6}
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    current_workspace = api.vars.current_workspace
```

---

## todos_tree

```py
def todos_tree(self) -> Optional[TodosTree]
```

Returns the todos tree for the current workspace if available; otherwise, returns `None`

```py{6}
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    todos_tree = api.vars.todos_tree
```

---

## current_todo

```py
def current_todo(self) -> Optional[Todo]
```

Returns the currently highlighted todo item if available; otherwise, returns `None` (see [todo](../backend/todo.md))

```py{6}
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    current_todo = api.vars.current_todo
```
