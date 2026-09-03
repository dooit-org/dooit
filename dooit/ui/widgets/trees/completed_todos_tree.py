from datetime import datetime
from typing import Any, Dict, List, Optional

from textual import on

from dooit.api import FixedProject, Todo, TodoGroup, manager
from dooit.api.fixed_projects import completion_key
from .fixed_todos_tree import FixedTodosTree
from .model_tree import ModelTree


class CompletedTodosTree(FixedTodosTree):
    """
    The pane of a fixed project whose rows are the todos already done

    Unticking a todo anywhere else takes it out of the pane it was in and puts
    it back among the work still to do. Doing that here would drop the row out
    of the only pane it is in, mid-thought, before anything could be said
    about when the todo is supposed to happen now.

    So the row is held instead: it stays where it was sitting, unticked and
    edited like a row in any other pane, and is let go of once that edit has
    been confirmed — or once the cursor has walked away without one. The todo
    itself is back in its project the whole time; what is held is the row.
    """

    def __init__(self, model: FixedProject) -> None:
        super().__init__(model)

        # The rows being sent back, each under the date it was ordered by
        # while it was still completed, so that it keeps its place in the pane
        # for as long as it is being worked on
        self._held: Dict[str, Optional[datetime]] = {}

    def _held_todos(self) -> List[Todo]:
        """
        The todos still being held

        Dropping the ones there is nothing left to hold: a row deleted from
        under the cursor, and one ticked off again, which the project itself
        hands back now.
        """

        todos = []

        for uuid in list(self._held):
            todo = manager.session.get(Todo, int(uuid.rsplit("_", 1)[-1]))

            if todo is None or todo.is_completed:
                self._held.pop(uuid)
                continue

            todos.append(todo)

        return todos

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

        # The pane is one flat run of rows ordered by date, so a row on its
        # way out goes back in at the date it had while it was still one of
        # them, rather than dropping to the end of the run it is leaving
        todos = [todo for group in groups for todo in group.todos] + held
        todos.sort(key=self._order_key, reverse=True)

        return [TodoGroup(todos=todos)]

    def column_value(self, attr: str, component: Any) -> Any:
        """
        A held row still shows the date it was completed on

        That date is what the row is sitting at, and dropping it the moment
        the tick came off would leave the row in the middle of the pane with
        nothing left to say why it is there.
        """

        if attr in self.model.extra_columns:
            uuid = component.model.uuid

            if uuid in self._held:
                return self._as_shown(attr, self._held[uuid])

        return super().column_value(attr, component)

    def toggle_complete(self):
        todo = self.current_model
        assert isinstance(todo, Todo)

        if todo.is_completed:
            # Unticking is the first half of filing the todo back where it
            # came from; the row is kept for the second half
            self._held[todo.uuid] = todo.completed_at
        else:
            # Ticked off again: a completed row like any other from here on,
            # ordered by the date it has just been given
            self._held.pop(todo.uuid, None)

        super().toggle_complete()

    def stop_edit(self):
        held = self.current_model.uuid if self.highlighted is not None else None

        super().stop_edit()

        # The edit is the second half: whatever had to be said about the todo
        # on its way back has been said, so the row it was typed into goes
        if held in self._held:
            self._held.pop(held)
            self.force_refresh()

    @on(ModelTree.OptionHighlighted)
    def release_rows_walked_away_from(
        self, event: ModelTree.OptionHighlighted
    ) -> None:
        """
        Lets go of a held row the cursor has left

        It was kept back for an edit that never came, and a row nobody is
        working on has nothing left to wait for.
        """

        if not self._held:
            return

        left_behind = set(self._held) - {event.option_id}

        if not left_behind:
            return

        for uuid in left_behind:
            self._held.pop(uuid)

        self.force_refresh()
