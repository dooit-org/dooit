<style>
h2 code {
    color: var(--vp-c-brand-1);
}
</style>

# Dooit Vars

This api component exposes some of the stuff running on dooit + act as a global register to tweak settings \
Its still developing and I'll add more stuff to it as per demand!

## `editable` always_expand_projects

If set to `True`, the projects will always be expanded

```py
def always_expand_projects(self) -> bool
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
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

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
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

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
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    theme = api.vars.theme
```

---

## `readonly` projects_tree

```py
def projects_tree(self) -> ProjectsTree
```

Returns the current projects tree object

```py{6}
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    projects_tree = api.vars.projects_tree
```

---

## `readonly` current_project

```py
def current_project(self) -> Optional[Project]
```

Returns the currently highlighted project object if available; otherwise, returns `None` (see [project](../backend/project.md))

```py{6}
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    current_project = api.vars.current_project
```

---

## `readonly` todos_tree

```py
def todos_tree(self) -> Optional[TodosTree]
```

Returns the todos tree for the current project if available; otherwise, returns `None`

```py{6}
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

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
from dooit.ui.api.events import DooitEvent
from dooit.ui.api import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    current_todo = api.vars.current_todo
```
