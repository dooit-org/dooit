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
    """
    SQLAlchemy declarative base for all dooit database models.
    """

    pass


class BaseModelMixin:
    """
    Mixin that provides automatic table name generation from the class name.
    """

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
        """
        Return a list of column names that can be used for sorting and comparison.
        """

        to_ignore = ["id", "order_index", "is_root"]

        comparable_fields = [
            column.name
            for column in inspect(cls).columns
            if not column.name.endswith("_id") and column.name not in to_ignore
        ]

        return comparable_fields

    @property
    def uuid(self) -> str:
        """Return a unique identifier string combining the class name and id."""
        return f"{self.__class__.__name__}_{self.id}"

    @property
    def parent(self) -> Any:
        """Return the parent node of this model."""
        raise NotImplementedError  # pragma: no cover

    @property
    def nest_level(self):
        """Return the nesting depth of this node relative to its top-level ancestor."""

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
        """Return a list of sibling nodes sharing the same parent."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def from_id(cls, _id: str) -> Self:
        """Look up and return a model instance by its string identifier."""
        raise NotImplementedError  # pragma: no cover

    @property
    def session(self):
        """Return the current SQLAlchemy session from the manager."""
        return manager.session

    def is_last_sibling(self) -> bool:
        """Check whether this node is the last among its siblings."""
        return self.siblings[-1].id == self.id

    def is_first_sibling(self) -> bool:
        """Check whether this node is the first among its siblings."""
        return self.siblings[0].id == self.id

    @property
    def has_same_parent_kind(self) -> bool:
        """Check whether the parent is the same type as this node."""
        raise NotImplementedError  # pragma: no cover

    def sort_siblings(self, field: str):
        """Sort sibling nodes by the given field name."""
        raise NotImplementedError  # pragma: no cover

    def reverse_siblings(self):
        """Reverse the ordering of all siblings."""

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
        """Create and return a new sibling node adjacent to this one."""
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
        """Delete this node from the database."""
        manager.delete(self)

    def save(self) -> None:
        """Persist this node to the database."""
        manager.save(self)

    @staticmethod
    def clone_from_id(id: int, order_index: int) -> "DooitModel":
        """Create a duplicate of the model identified by the given id."""
        raise NotImplementedError
