<style>
h2 code {
    color: var(--vp-c-brand-1);
}
</style>

<!-- ------------------------------------ -->

# Dooit API

DooitAPI is an api object that you'll use in your config to configure everything in dooit's ui \
All the next sections will walk you through all the functions provided by the api

There are two things that you need to know of:

- The api has certain functions to perform some particular tasks
- The api also exposes other sub modules which you can find in other section for configurations

:::tip :bulb: TIP
You probably wont need to deep dive too much into api functions, check out [`Default Keys from config`](/extra/moving_from_v2#new-4) as probably everything is already set to sane defaults
:::

### Sub-modules
------------

- [`keys`](./keys.md)
- [`layout`](./layout.md)
- [`formatter`](./formatter.md)
- [`bar`](./bar.md)
- [`vars`](./vars.md)
- [`dashboard`](./dashboard.md)

### Functions

```py
@subscribe(Startup)
def setup(api: DooitAPI, _):
    api.<Your function here>
```

## `method` quit

Quits the app

## `method` notify

Create a notification to show in the bar

**Parameters:**

| Param|<div style="width: 100px">Default</div> |Description|
| ------------- | :----------------:  | :----------------------------------------------------------------------------------------|
| message       |                     | The message to show on the bar                                                           |
| level         | `"info"`            | The level of the message. Can be `info`, `warning` or `error`                            |

## `method` add_child_node

Add a child to the highlighted item

## `method` add_sibling

Add a sibling to the highlighted item

## `method` copy_description_to_clipboard

Copy the description of the selected node to clipboard

## `method` copy_model

Copy the focused model to clipboard

## `method` paste_model_above

Paste the model from clipboard above the focused item

## `method` paste_model_below

Paste the model from clipboard below the focused item

## `method` decrease_urgency

Decrease the urgency of the todo

## `method` edit_description

Start editing the description of the focused item

## `method` edit_due

Start editing the due date of the todo

## `method` edit_effort

Start editing the effort of the todo

## `method` edit_recurrence

Start editing the recurrence of the todo

## `method` go_to_bottom

Move the cursor to the bottom of the list

## `method` go_to_top

Move the cursor to the top of the list

## `method` increase_urgency

Increase the urgency of the todo

## `method` move_down

Move the cursor down in the focused list

## `method` move_up

Move the cursor up in the focused list

## `method` no_op

No operation function

## `method` remove_node

Remove the highlighted item

## `method` shift_down

Shift the highlighted item down

## `method` shift_up

Shift the highlighted item up

## `method` show_help

Show the help screen

## `method` start_search

Start a search within the list

## `method` start_sort

Start sorting the siblings of the highlighted item

## `method` switch_focus

Switch focus between the workspace and the todo list

## `method` toggle_complete

Toggle the completion of the todo

## `method` toggle_expand

Toggle the expansion of the highlighted item

## `method` toggle_expand_parent

Toggle the expansion of the parent of the highlighted item
