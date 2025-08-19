# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# 3.3.3

### Added

- Allow users to copy todo or workspace object as whole to paste it somewhere else (#209) [see api docs](https://dooit-org.github.io/dooit/configuration/dooit_api.html)

# 3.2.3

### Added

- Allow `enter` key to be used for edit confirmation (#238)

## 3.2.2

### Fixed
- Siblings addition was messed up due to incorrect update

## 3.2.1

### Fixed
- Dooit crash on Zero/Null values for effort and urgency (#234)

## 3.2.0

### Added

- vars `always_expand_workspaces` and `always_expand_todos`
- Support for latest textual (#229, #231, #232)
- Add support for using custom database for todos (#224)

### Fixed
- Pending status getting resetted on sibling addition (#222)
- Child task status reset when editing parent task (#227)

### Changed

- `dev only` We can now set order index arbitrarily and the todo position will adjust itself

## 3.1.0

### Added

- Add `get_formatter_by_id` to formatters
- Add functionality to yank descriptions from todo and workspaces
- Add `-c/--config` flag for running custom configs

### Fixed

- Question Mark shows help me while editing text (#214)
- SqlOperationError on windows (#210)
- Cant see the cursor when typing at the bottom of the screen (#218)

## 3.0.4

This is a minor release with no new changes but fixing some stuff that was caused by recent textual update
- Fix tint on focused lists
- Startup crash because of variable override (#207)

## 3.0.3

### Fixed

- Recurrence not working as expected (https://github.com/dooit-org/dooit/issues/204)
- Dooit crash on item delete and then addition (https://github.com/dooit-org/dooit/issues/205)
- Stuck on CONFIRM mode if deletions are fast
- Messed up column widths on sudden width changes
- Values not getting parsed because of whitespace

## 3.0.2

### Fixed
- Error while migrating data (https://github.com/dooit-org/dooit/issues/201)

## 3.0.1

### Fixed
- Start crash due to missing folder

## 3.0.0

### Added
- Brand new dooit api for configurations
- Snappier UI Experience
- Event based code execution via dooit api
- Customize the columns order and visibility for todos and workspaces
- Allow addition of custom keybinds to trigger certain functions
- Better optimized bar (wont block ui)
- Custom formatters for column values to suit your needs!
- Multiple Theme support
- Custom CSS injections into the UI
- Dooit will now confirm node deletion by default. This behaviour can be changed via config
+ many more...check out [the wiki](https://dooit-org.github.io/dooit/)

### Changed
- Sort options now appear in bar rather than a menu
- search will now show all items but will disable all non-matching ones
- Yanking was removed (will be introduced again as a plugin instead)

### Removed
- Now todos are no longer stored in `todo.yaml`, run dooit --migrate to migrate to new format
- Old config will no longer work, see the [latest docs](https://dooit-org.github.io/dooit/) to check out the configuration

> [!NOTE]
> The support for YAML will be dropped from v3.0.0

## 2.2.0

### Added
- Add support for changing the default urgency of a todo with `TODO.initial_urgency`
- Add support for changing urgency colors with `TODO.urgency1_color` to `TODO.urgency4_color`
- Add shortcut for recursively expanding and closing todos (Ctrl + Z)
- Add `WORKSPACE.start_expanded` and `TODO.start_expanded` to launch with the Workspace and Todo tree fully expanded
- Dooit can now also be launched with `python -m dooit`

### Fixed

- App crashes when an opened workspace is deleted (closes https://github.com/kraanzu/dooit/issues/169)
- App crash on adding a workspace (closes https://github.com/kraanzu/dooit/issues/167)

## 2.0.2

### Added
- Add `DATE_FORMAT` and `TIME_FORMAT` to allow users to customize due date https://github.com/kraanzu/dooit/issues/141 (Also [see this](https://github.com/kraanzu/dooit/wiki/Configuration#general))

## 2.0.1

### Added
- Add `USE_DAY_FIRST` settings to allow users to switch between day and month

### Fixed
- `Ctrl+q` did not exit the app (closes https://github.com/kraanzu/dooit/issues/140)


## 2.0.0

### Added
- Dooit now allows duplicate descriptions to be added(closes https://github.com/kraanzu/dooit/issues/113)
- Clear due date when selected (closes https://github.com/kraanzu/dooit/issues/111)
- Add support for h / l to switch between panes (closes https://github.com/kraanzu/dooit/issues/96)
- Add support for yank whole todos/workspaces (closes https://github.com/kraanzu/dooit/issues/76)
- Add support for `save on escape` (closes https://github.com/kraanzu/dooit/issues/106)
- Add support for opening and highlighting urls (closes https://github.com/kraanzu/dooit/issues/108)
- Add support for changing due date format (due/remaining time) (closes https://github.com/kraanzu/dooit/issues/116)

### Fixed
- Slowness due to un-necessary rendering of the app
- Slow loading of app because of dateparser (see https://github.com/kraanzu/dooit/issues/136)
- Text disappearing for non-alphabet characters in description(closes https://github.com/kraanzu/dooit/issues/112)
- Todos disappearing when wrapping descriptions with tags/quotes/brackets (closes https://github.com/kraanzu/dooit/issues/107)
- Use background color specified in config for help menu
- Bar did not pick color from config and used the regular background

### Breaking Changes
- Tags are now built-in within the description. They start with @ symbol (eg bring milk @chore)
- Todos are no longer stored in a todo.txt format yaml file. This shouldn't break anything and the new version will take care of that!

## 1.0.1

### Fixed
- File not found error on windows (closes https://github.com/kraanzu/dooit/issues/91)
- crash for python <= 3.10 (closes https://github.com/kraanzu/dooit/issues/99)

## 1.0.0

### Added

- **A whole new API to interact with dooit** (closes https://github.com/kraanzu/dooit/issues/23)
- **Unlimited branching of todos and workspaces** (closes https://github.com/kraanzu/dooit/issues/85 and https://github.com/kraanzu/dooit/issues/70 and https://github.com/kraanzu/dooit/issues/58)
- **Smart node addition on <enter>**
  - Dooit now will not add an extra item automatically if you are just editing description of some node
- **Support for edit and addition in SEARCH mode**
  - Previously users were only allowed to jump to the todo
- **Synchronisation between multiple instances**
  - Previously dooit printed a warning and exited with a message indicating that it's already running (closes https://github.com/kraanzu/dooit/issues/49)
- **New parameters for todos!**
  - **Recurrence** ==> Adds recurrence to todos for regular reminder!
  - **Effort** ==> An Integer Value to determine the effort/time it will take to complete the todo (for https://github.com/kraanzu/dooit/issues/74)
  - **Tags** ==> Add tags to todos
  - **Time** ==> Previously only date was supported (closes https://github.com/kraanzu/dooit/issues/66)
- **Better date&time parsing**
  - Dooit now uses [dateparser](https://pypi.org/project/dateparser/) module to make it a lot easier to add and edit date&time (for https://github.com/kraanzu/dooit/issues/71)
- **Custiomizable Bar**
  - Dooit now has a bar that can be customized to your liking!
  - You can now use python scripts to display your desired content in the bar
  - You can also use dooit API to display info in status bars
- A better config parser which handles ovveriden case better! (closes https://github.com/kraanzu/dooit/issues/64)

### Fixed
  - Update textual which might fix several issues! (maybe closes https://github.com/kraanzu/dooit/issues/57 and https://github.com/kraanzu/dooit/issues/57)
  - Using '/' in todos crashes app (closes https://github.com/kraanzu/dooit/issues/84)


### Changed
  - Remove mouse support...coz why not? (closes https://github.com/kraanzu/dooit/issues/69)
  - Some keybindings
  - Unicode by default (remove nerd font icons from default config)
  - match-case stmts (Adds support for python>=3.7)
