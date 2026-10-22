from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class SourceKind(StrEnum):
    """The data sources the ids come from."""

    INTERNAL = "internal"
    EXTERNAL = "external"


class RouteIdentifier(ABC):
    """Identifier of an entity that lives in a concrete data source.

    Internal ids are integers, external ones are strings. Equality is
    defined once here, by the hash, so ids are comparable and can be used
    as dict and set members.
    """

    @property
    @abstractmethod
    def source(self) -> SourceKind:
        """The data source the identifier belongs to."""

    @abstractmethod
    def __str__(self) -> str:
        """The canonical form, used to build the cache keys."""

    @abstractmethod
    def __hash__(self) -> int:
        """A stable hash of the identifier."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RouteIdentifier):
            return NotImplemented
        return hash(self) == hash(other)


@dataclass(frozen=True, eq=False)
class InternalId(RouteIdentifier):
    """Identifier of an entity of our own database."""

    value: int

    @property
    def source(self) -> SourceKind:
        return SourceKind.INTERNAL

    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash((SourceKind.INTERNAL, self.value))


@dataclass(frozen=True, eq=False)
class ExternalId(RouteIdentifier):
    """Identifier of an entity of an external source."""

    value: str

    @property
    def source(self) -> SourceKind:
        return SourceKind.EXTERNAL

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash((SourceKind.EXTERNAL, self.value))
