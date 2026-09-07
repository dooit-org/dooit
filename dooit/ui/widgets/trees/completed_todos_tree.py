from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.text import Text
from textual import on

from dooit.api import FixedProject, Todo, TodoGroup, manager, revive_home
from dooit.api.fixed_projects import completion_key
from .fixed_todos_tree import FixedTodosTree
from .model_tree import ModelTree


def family_root(todo: Todo) -> Todo:
    """
    The task a todo belongs to: itself, or whatever it is a step of
    """

    node = todo

    while node.parent_todo is not None:
        node = node.parent_todo

    return node


class CompletedTodosTree(FixedTodosTree):
    """
    The pane of a fixed project whose rows are the tasks already done

    A row here is a whole task: one finished todo, with the steps that were
    finished along with it drawn underneath it the way its own project drew
    them. Nothing arrives on its own until the whole of it is done.

    Unticking a todo anywhere else takes it out of the pane it was in and puts
    it back among the work still to do. Doing that here would drop the row out
    of the only pane it is in, mid-thought, before anything could be said
    about when the task is supposed to happen now.

    So the task is held instead: it stays where it was sitting, unticked and
    edited like a row in any other pane, and is let go of once that edit has
    been confirmed — or once the cursor has walked away without one. Held
    whole, whichever of its rows was unticked, since unticking any step of a
    task sends the task itself back: what is held is never half a family.
    """

    show_children = True

    # Rows are whole tasks and the steps under them, so the pane draws the
    # same guides the project it came from does; the flat panes have nothing
    # to draw them for
    show_guides = True

    def __init__(self, model: FixedProject) -> None:
        super().__init__(model)

        # The tasks being sent back, each under the date it was ordered by
        # while it was still completed, so that it keeps its place in the pane
        # for as long as it is being worked on
        self._held: Dict[str, Optional[datetime]] = {}

    def _held_todos(self) -> List[Todo]:
        """
        The tasks still being held

        Dropping the ones there is nothing left to hold: a row deleted from
        under the cursor, and one ticked off again, which the project itself
        hands back now.
        """

        todos = []

        for uuid in list(self._held):
            todo = self._todo_from_uuid(uuid)

            if todo is None or todo.is_completed:
                self._held.pop(uuid)
                continue

            todos.append(todo)

        return todos

    @staticmethod
    def _todo_from_uuid(uuid: Optional[str]) -> Optional[Todo]:
        if not uuid or not uuid.startswith(f"{Todo.__name__}_"):
            return None

        return manager.session.get(Todo, int(uuid.rsplit("_", 1)[-1]))

    def _root_uuid(self, uuid: Optional[str]) -> Optional[str]:
        """
        The uuid of the task a row belongs to, which is what is held
        """

        todo = self._todo_from_uuid(uuid)

        return None if todo is None else family_root(todo).uuid

    def _order_key(self, todo: Todo) -> datetime:
        if todo.uuid in self._held:
            return self._held[todo.uuid] or datetime.min

        return completion_key(todo)

    @property
    def todo_groups(self) -> List[TodoGroup]:
        groups = super().todo_groups
        held = self._held_todos()

        if not held:
            return groups

        # The pane is one run of tasks ordered by date, so a task on its way
        # out goes back in at the date it had while it was still one of them,
        # rather than dropping to the end of the run it is leaving
        todos = [todo for group in groups for todo in group.todos] + held
        todos.sort(key=self._order_key, reverse=True)

        return [TodoGroup(todos=todos)]

    def row_note(self, model) -> Text:
        """
        Only a task says which project it came out of

        The steps under it came out of the same one, and saying so on every
        row of a family would say it three times over.
        """

        if isinstance(model, Todo) and model.parent_todo is not None:
            return Text()

        return super().row_note(model)

    def column_value(self, attr: str, component: Any) -> Any:
        """
        A held row still shows the date its task was completed on

        That date is what the row is sitting at, and dropping it the moment
        the tick came off would leave the family in the middle of the pane
        with nothing left to say why it is there.
        """

        value = super().column_value(attr, component)

        if value is not None or attr not in self.model.extra_columns:
            return value

        held = self._held.get(self._root_uuid(component.model.uuid))

        if held is None:
            return value

        return self._as_shown(attr, held)

    def toggle_complete(self):
        todo = self.current_model
        assert isinstance(todo, Todo)

        root = family_root(todo)

        if todo.is_completed:
            # Unticking is the first half of filing the task back where it
            # came from; the rows are kept for the second half
            self._held[root.uuid] = root.completed_at
        else:
            # Ticked off again: a completed task like any other from here on,
            # ordered by the date it has just been given
            self._held.pop(root.uuid, None)

        super().toggle_complete()

        # A finished task can sit in the log with no project at all: the one it
        # was filed under was thrown away while it was in here. The moment
        # there is work left in it again it needs somewhere to be done, so the
        # project it names is built back to take it
        if root.is_pending:
            self.announce_revived(revive_home(root))

    def stop_edit(self, cancel: bool = False):
        held = None

        if self.highlighted is not None:
            held = self._root_uuid(self.current_model.uuid)

        super().stop_edit(cancel)

        # The edit is the second half: whatever had to be said about the task
        # on its way back has been said, so the rows it was typed into go
        if held in self._held:
            self._held.pop(held)
            self.force_refresh()

    @on(ModelTree.OptionHighlighted)
    def release_rows_walked_away_from(
        self, event: ModelTree.OptionHighlighted
    ) -> None:
        """
        Lets go of a held task the cursor has left

        It was kept back for an edit that never came, and a task nobody is
        working on has nothing left to wait for. The cursor is still on it
        wherever in the family it sits: walking from a task to one of its
        steps is not walking away from it.
        """

        if not self._held:
            return

        left_behind = set(self._held) - {self._root_uuid(event.option_id)}

        if not left_behind:
            return

        for uuid in left_behind:
            self._held.pop(uuid)

        self.force_refresh()
