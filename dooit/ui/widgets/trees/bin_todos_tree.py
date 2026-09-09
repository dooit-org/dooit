from .fixed_todos_tree import FixedTodosTree


class BinTodosTree(FixedTodosTree):
    """
    The pane of a fixed project whose rows are the tasks that were thrown away

    A row here is a whole task: one binned todo, with the steps that went in
    with it drawn underneath it the way its own project drew them. It is the
    same pane the completion log is, read the same way — newest at the top,
    each row saying which project it came out of — and the one place in dooit
    where a row can be brought back rather than only worked on.

    Nothing is ticked off in here. A task in the Bin is not work that is being
    done or not done any more; the two things there are to do with it are put
    it back and be rid of it, and both are keys of their own.
    """

    shows_binned = True

    # Rows are whole tasks and the steps under them, so the pane draws the
    # same guides the project it came from does
    show_children = True
    show_guides = True

    def toggle_complete(self):
        self._not_here("Tasks can't be ticked off")
