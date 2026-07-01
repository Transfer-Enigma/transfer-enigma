import datetime
from abc import ABC, abstractmethod

from sqlalchemy import BinaryExpression, and_, true


class Filter(ABC):
    """Base filter for segment conditions."""

    @abstractmethod
    def to_sql(self, alias: object, date: datetime.date, dep_id: int, dest_id: int) -> BinaryExpression:
        ...


class EffectiveOn(Filter):
    """Filter by date range (effective_from <= date <= effective_to)."""

    def to_sql(self, alias: object, date: datetime.date, dep_id: int, dest_id: int) -> BinaryExpression:
        return and_(
            alias.effective_from <= date,  # type: ignore[attr-defined]
            alias.effective_to >= date,  # type: ignore[attr-defined]
        )


class AtStartPoint(Filter):
    """Filter by start point ID (uses dep_id parameter)."""

    def __init__(self, start_id: int | None = None) -> None:
        self.start_id = start_id

    def to_sql(self, alias: object, date: datetime.date, dep_id: int, dest_id: int) -> BinaryExpression:
        point_id = dep_id if self.start_id is None else self.start_id
        if point_id is not None:
            return alias.start_point_id == point_id  # type: ignore[attr-defined]
        return true()


class AtEndPoint(Filter):
    """Filter by end point ID (uses dest_id parameter)."""

    def __init__(self, end_id: int | None = None) -> None:
        self.end_id = end_id

    def to_sql(self, alias: object, date: datetime.date, dep_id: int, dest_id: int) -> BinaryExpression:
        point_id = dest_id if self.end_id is None else self.end_id
        if point_id is not None:
            return alias.end_point_id == point_id  # type: ignore[attr-defined]
        return true()


class ExcludeOwners(Filter):
    """Exclude routes with specific container owners."""

    def __init__(self, owners: list) -> None:
        self.owners = owners

    def to_sql(self, alias: object, date: datetime.date, dep_id: int, dest_id: int) -> BinaryExpression:
        if self.owners:
            return alias.container_owner.notin_(self.owners)  # type: ignore[attr-defined]
        return true()


class NoDropOff(Filter):
    """Filter for routes without drop-off point."""

    def to_sql(self, alias: object, date: datetime.date, dep_id: int, dest_id: int) -> BinaryExpression:
        return alias.dropp_off_point_id.is_(None)  # type: ignore[attr-defined]
