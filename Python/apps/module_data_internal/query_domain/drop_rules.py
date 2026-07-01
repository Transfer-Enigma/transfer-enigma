import datetime
from abc import ABC, abstractmethod

from sqlalchemy import BinaryExpression, and_


class DropRule(ABC):
    """Base rule for drop-off connections."""

    @abstractmethod
    def to_sql(
        self,
        from_alias: object,
        to_alias: object,
        drop_alias: object,
        from_price_alias: object,
        to_price_alias: object,
        date: datetime.date,
    ) -> BinaryExpression:
        ...


class DropMatchesEndpoint(DropRule):
    """Drop-off matches the 'to' segment endpoints."""

    def to_sql(
        self,
        from_alias: object,
        to_alias: object,
        drop_alias: object,
        from_price_alias: object,
        to_price_alias: object,
        date: datetime.date,
    ) -> BinaryExpression:
        return and_(
            to_alias.start_point_id == drop_alias.start_point_id,  # type: ignore[attr-defined]
            to_alias.end_point_id == drop_alias.end_point_id,  # type: ignore[attr-defined]
        )


class DropMatchesCompany(DropRule):
    """Drop-off matches the 'from' segment company."""

    def to_sql(
        self,
        from_alias: object,
        to_alias: object,
        drop_alias: object,
        from_price_alias: object,
        to_price_alias: object,
        date: datetime.date,
    ) -> BinaryExpression:
        return from_alias.company_id == drop_alias.company_id  # type: ignore[attr-defined]


class DropMatchesContainer(DropRule):
    """Drop-off matches the 'to' segment container."""

    def to_sql(
        self,
        from_alias: object,
        to_alias: object,
        drop_alias: object,
        from_price_alias: object,
        to_price_alias: object,
        date: datetime.date,
    ) -> BinaryExpression:
        return to_price_alias.container_id == drop_alias.container_id  # type: ignore[attr-defined]


class DropEffectiveOn(DropRule):
    """Drop-off must be valid on the shipping date."""

    def to_sql(
        self,
        from_alias: object,
        to_alias: object,
        drop_alias: object,
        from_price_alias: object,
        to_price_alias: object,
        date: datetime.date,
    ) -> BinaryExpression:
        return and_(
            drop_alias.effective_from <= date,  # type: ignore[attr-defined]
            drop_alias.effective_to >= date,  # type: ignore[attr-defined]
        )
