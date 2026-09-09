from typing import Any, Generic, TypeVar

from dooit.api import DooitModel
from ._input import Input

ModelType = TypeVar("ModelType", bound=DooitModel)
ModelValue = TypeVar("ModelValue", bound=Any)


class SimpleInput(Input, Generic[ModelType, ModelValue]):
    """
    A simple single line Text Input widget
    """

    _cursor_pos: int = 0
    _cursor: str = "|"

    def __init__(self, model: ModelType) -> None:
        self.model = model

        default_value = self._get_default_value()
        super().__init__(value=default_value)

        self.reset()

    def _get_default_value(self) -> str:
        return str(self.model_value)

    @property
    def _property(self) -> str:
        return self.__class__.__name__.lower()

    @property
    def model_value(self) -> ModelValue:
        return getattr(self.model, self._property)

    @model_value.setter
    def model_value(self, value: str) -> None:
        return setattr(self.model, self._property, value)

    def _typecast_value(self, value: str) -> Any:
        return value

    def reset(self) -> str:
        self._cursor_pos = len(self.value)
        return self.value

    def start_edit(self) -> None:
        """
        Begin an edit on what the model holds now, not what it held then

        A row is drawn straight off the model, so a field that was changed
        without being typed into - pasted in, say - shows the new value while
        this buffer still holds the one the renderer was built with. Filling
        it here is what keeps the two the same thing.
        """

        self._value = self._get_default_value()
        super().start_edit()
        self.move_cursor_to_end()

    def stop_edit(self, cancel: bool = False) -> None:
        """
        End the edit, writing the buffer back to the model unless it is thrown
        away

        A cancelled edit never touches the model: the buffer is refilled from
        what the model still holds, which is what puts the field back the way
        it was before the first keystroke.
        """

        if cancel:
            self._value = self._get_default_value()
            super().stop_edit(cancel)
            self.move_cursor_to_end()
            return

        self._value = self.value.strip()
        try:
            self.model_value = self._typecast_value(self.value)
            self.model.save()
        finally:
            self._value = self._get_default_value()
            super().stop_edit()
            self.move_cursor_to_end()

    def keypress(self, key: str) -> None:
        super().keypress(key)
