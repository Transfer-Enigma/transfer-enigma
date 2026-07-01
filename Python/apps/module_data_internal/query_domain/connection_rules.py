from abc import ABC, abstractmethod

from sqlalchemy import BinaryExpression


class ConnectionRule(ABC):
    """Base rule for segment connections."""

    @abstractmethod
    def to_sql(self, from_alias: object, to_alias: object) -> BinaryExpression:
        ...


class MatchesEndpoint(ConnectionRule):
    """Strict endpoint matching: from.end_point == to.start_point."""

    def to_sql(self, from_alias: object, to_alias: object) -> BinaryExpression:
        return from_alias.end_point_id == to_alias.start_point_id  # type: ignore[attr-defined]
