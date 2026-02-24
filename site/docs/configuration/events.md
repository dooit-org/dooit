# Dooit Events

Dooit emits event when certain things happen, you can use `@subscribe` or `@timer` to execute code when that event fires


### Timer Usage

:::info :grey_exclamation: NOTE
Timer is not an event, it just tells dooit to update a function every `X` seconds
:::

``` python
from dooit.ui.bridge import DooitAPI, timer

@timer(1) # in seconds
def foo(api: DooitAPI):
    # your code here
```

### Subscribe Usage

Subscribe can be used to execute and update values of function on a particular event
It takes in two parameters: `api` and `event` which are a copy of dooit api and the event respectively

``` python
from dooit.ui.bridge.events import DooitEvent
from dooit.ui.bridge import DooitAPI, subscribe

@subscribe(DooitEvent)
def foo(api: DooitAPI, event: DooitEvent):
    # your code here
```

You can find all the available events below

## DooitEvent

Triggered for all dooit events.


## WorkspaceEvent

Triggered for all workspace related events i.e. `creation`/`modification`/`deletion` etc.

**Parameters:**

| Param      | <div style="width: 100px">Default</div> | Description                                        |
|------------|:--------------------------------------:|----------------------------------------------------|
| workspace  |                                        | The workspace object associated with the event.     |


## TodoEvent

Triggered for all todo related events i.e. `creation`/`modification`/`deletion` etc.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                                   |
|-------|:--------------------------------------:|-----------------------------------------------|
| todo  |                                        | The todo object associated with the event.     |


## Startup

Triggered when the app starts.


## ShutDown

Triggered when the user presses the exit app keybind.


## SwitchTab

Triggered when the user switches focus to another pane.


## SpawnHelp

Triggered when the user presses `?` in `NORMAL` mode.


## ModeChanged

Triggered when there is a change in the `status` mode.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                             |
|-------|:--------------------------------------:|-----------------------------------------|
| mode  |                                        | The new mode (`ModeType`) that was set. |


## StartSearch

Triggered when the user initiates a search operation.

## StartSort

Triggered when the user initiates a sort operation.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                                   |
|-------|:--------------------------------------:|-----------------------------------------------|
| model |                                        | The model (`Todo` or `Workspace`) to be sorted.        |


## ShowConfirm

Triggered when a user confirmation is required.

## WorkspaceSelected

Triggered when the user selects a workspace.

**Parameters:**

| Param      | <div style="width: 100px">Default</div> | Description                                        |
|------------|:--------------------------------------:|----------------------------------------------------|
| workspace  |                                        | The workspace object selected by the user.          |


## WorkspaceRemoved

Triggered when the user removes a workspace.

**Parameters:**

| Param      | <div style="width: 100px">Default</div> | Description                                        |
|------------|:--------------------------------------:|----------------------------------------------------|
| workspace  |                                        | The workspace object that was removed.             |


## WorkspaceDescriptionChanged

Triggered when the user updates the description of a workspace.

**Parameters:**

| Param      | <div style="width: 100px">Default</div> | Description                                                   |
|------------|:--------------------------------------:|---------------------------------------------------------------|
| old        |                                        | The previous description of the workspace.                     |
| new        |                                        | The updated description of the workspace.                     |
| workspace  |                                        | The workspace object whose description was changed.           |


## TodoSelected

Triggered when the user selects a todo.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                                |
|-------|:--------------------------------------:|--------------------------------------------|
| todo  |                                        | The todo object selected by the user.       |


## TodoRemoved

Triggered when the user removes a todo.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                         |
|-------|:--------------------------------------:|-------------------------------------|
| todo  |                                        | The todo object that was removed.   |


## TodoDescriptionChanged

Triggered when the user updates the description of a todo.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                                       |
|-------|:--------------------------------------:|---------------------------------------------------|
| old   |                                        | The previous description of the todo.             |
| new   |                                        | The updated description of the todo.              |
| todo  |                                        | The todo object whose description was changed.    |


## TodoDueChanged

Triggered when the user updates the due date of a todo.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                                    |
|-------|:--------------------------------------:|------------------------------------------------|
| old   |                                        | The previous due date of the todo.             |
| new   |                                        | The updated due date of the todo.              |
| todo  |                                        | The todo object whose due date was changed.    |


## TodoStatusChanged

Triggered when the user updates the status of a todo.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                                    |
|-------|:--------------------------------------:|------------------------------------------------|
| old   |                                        | The previous status of the todo.               |
| new   |                                        | The updated status of the todo.                |
| todo  |                                        | The todo object whose status was changed.      |


## TodoEffortChanged

Triggered when the user updates the effort level of a todo.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                                     |
|-------|:--------------------------------------:|-------------------------------------------------|
| old   |                                        | The previous effort level of the todo.          |
| new   |                                        | The updated effort level of the todo.           |
| todo  |                                        | The todo object whose effort level was changed. |


## TodoRecurrenceChanged

Triggered when the user updates the recurrence of a todo.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                                         |
|-------|:--------------------------------------:|-----------------------------------------------------|
| old   |                                        | The previous recurrence interval of the todo.        |
| new   |                                        | The updated recurrence interval of the todo.         |
| todo  |                                        | The todo object whose recurrence interval was changed. |


## TodoUrgencyChanged

Triggered when the user updates the urgency level of a todo.

**Parameters:**

| Param | <div style="width: 100px">Default</div> | Description                                     |
|-------|:--------------------------------------:|-------------------------------------------------|
| old   |                                        | The previous urgency level of the todo.         |
| new   |                                        | The updated urgency level of the todo.          |
| todo  |                                        | The todo object whose urgency level was changed. |
