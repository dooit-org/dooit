# Basics

This little guide will walk you through some of the basics about using dooit

## Help Menu

You can launch the help menu for dooit by pressing the `?` key. It'll show you all the keybinds currently attached

## Entering Data

There are multiple kinds of columns in dooit to fill.

### Descriptions

Both projects and todos have a description column, as the name suggests, you can enter a bunch of words into it \
For todos, you can use `@` in front of words to make it a `label`/`tag`. It doesn't hold any special meaning but yea

### Status

All todos have three kinds of status: `compeleted`,`pending` or `overdue` \
Overdue means the task is pending but the due date has already passed \
Via the TUI, you can toggle the status of the todo as `pending` or `not pending`

### Urgency

There are 4 levels of urgency, which are `1`, `2`, `3` and `4` \
where `4` and `1` are the `highest` and `lowest` urgency/priority respectively

### Due

:::info :grey_exclamation: INFO
Dooit uses [python-dateutil](https://pypi.org/project/python-dateutil/) under the hood to parse
:::

Due dates can be entered in other forms rather than DDMMYYY format, for example: \
You could write `1 jan 2025` and dooit will parse it


### Effort

In todos, effort is just a number, it doesnt mean anything and you could set it to whatevery you want: \
Effort points, time needed to complete, streak etc

***NOTE:*** You can further use the [`Formatters`](../configuration/formatter.md) to make it customize its format as well


### Recurrence

Like all other todo apps out therem, dooit also has an option to add a recurrence time

Its an interval value as to when a certain task should repeat itself \
For example, `1 day ` or `1 week`

You can use the format to set it:

`<number><legend>` <span style="opacity: 0.5;"># Example: 1d</span>

| Legend | Description |
|--------|-------------|
| `m`    | minute      |
| `h`    | hour        |
| `d`    | day         |
| `w`    | week        |
