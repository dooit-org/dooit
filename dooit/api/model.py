import uuid
from typing import Any, List, Literal, TypeVar
from typing_extensions import Self
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import inspect
from .manager import manager


SortMethodType = Literal["description", "status", "due", "urgency", "effort"]
T = TypeVar("T")


class BaseModel(DeclarativeBase):
    pass


class BaseModelMixin:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


def generate_unique_id():
    return uuid.uuid4().int & (2**62 - 1)


class DooitModel(BaseModel, BaseModelMixin):
    """
    Model class to for the base tree structure
    """

    __abstract__ = True

    # id: Mapped[int] = mapped_column(primary_key=True, default=generate_unique_id)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_index: Mapped[int] = mapped_column(default=-1)

    @classmethod
    def comparable_fields(cls):
        to_ignore = ["id", "order_index", "is_root"]

        comparable_fields = [
            column.name
            for column in inspect(cls).columns
            if not column.name.endswith("_id") and column.name not in to_ignore
        ]

        return comparable_fields

    @property
    def uuid(self) -> str:
        return f"{self.__class__.__name__}_{self.id}"

    @property
    def parent(self) -> Any:
        raise NotImplementedError  # pragma: no cover

    @property
    def nest_level(self):
        level = 0
        parent = self.parent

        while (
            parent
            and isinstance(self, parent.__class__)
            and not getattr(parent, "is_root", False)
        ):
            level += 1
            parent = parent.parent

        return level

    @property
    def siblings(self) -> List[Any]:
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def from_id(cls, _id: str) -> Self:
        raise NotImplementedError  # pragma: no cover

    @property
    def session(self):
        return manager.session

    def is_last_sibling(self) -> bool:
        return self.siblings[-1].id == self.id

    def is_first_sibling(self) -> bool:
        return self.siblings[0].id == self.id

    @property
    def has_same_parent_kind(self) -> bool:
        raise NotImplementedError  # pragma: no cover

    def sort_siblings(self, field: str):
        raise NotImplementedError  # pragma: no cover

    def reverse_siblings(self):
        for index, model in enumerate(reversed(self.siblings)):
            model.order_index = index

        manager.commit()

    def shift_up(self) -> bool:
        """
        Shift the item one place up among its siblings
        """

        if self.is_first_sibling():
            return False

        siblings = self.siblings
        index = siblings.index(self)
        siblings[index - 1].order_index += 1
        siblings[index].order_index -= 1

        self.session.add(siblings[index])
        self.session.add(siblings[index - 1])
        manager.commit()

        return True

    def _add_sibling(self) -> Self:
        raise NotImplementedError  # pragma: no cover

    def add_sibling(self):
        return self._add_sibling()

    def shift_down(self) -> bool:
        """
        Shift the item one place down among its siblings
        """

        if self.is_last_sibling():
            return False

        siblings = self.siblings
        index = siblings.index(self)
        siblings[index + 1].order_index -= 1
        siblings[index].order_index += 1

        self.session.add(siblings[index])
        self.session.add(siblings[index + 1])
        manager.commit()

        return True

    def drop(self) -> None:
        manager.delete(self)

    def save(self) -> None:
        manager.save(self)

    @staticmethod
    def clone_from_id(id: int, order_index: int) -> "DooitModel":
        raise NotImplementedError
