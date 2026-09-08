"""
Imported by pytest before any test module in this directory

`dooit.ui.widgets` and `dooit.ui.api` import each other, and the circle only
resolves when the walk into it starts from `dooit.ui.tui`. A test module whose
first dooit import is anything deeper — a bar, a tree — trips the cycle and
poisons the module cache for every file after it. Importing the base module
here settles the import order once, for the whole directory, and makes single
test files runnable on their own.
"""

import tests.test_ui.ui_base  # noqa: F401
