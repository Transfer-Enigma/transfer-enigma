from module_data_internal.query_domain.connection_rules import ConnectionRule
from module_data_internal.schemas import ContainerOwner
from sqlalchemy import BinaryExpression, and_, or_


class CocSocRule(ConnectionRule):
    """COC/SOC company matching logic."""

    def to_sql(self, from_alias: object, to_alias: object) -> BinaryExpression:
        return or_(
            to_alias.container_owner == ContainerOwner.SOC,  # type: ignore[attr-defined]
            and_(
                from_alias.company_id == to_alias.company_id,  # type: ignore[attr-defined]
                to_alias.container_owner == ContainerOwner.COC,  # type: ignore[attr-defined]
            ),
        )


class ThroughRule(ConnectionRule):
    """Through routes matching logic."""

    def to_sql(self, from_alias: object, to_alias: object) -> BinaryExpression:
        return or_(
            ~to_alias.is_through & ~from_alias.is_through,  # type: ignore[attr-defined]
            from_alias.company_id == to_alias.company_id,  # type: ignore[attr-defined]
        )


class DropAwareConnection:
    """Bridges segment connection and drop-off coupling for SEA→RAIL routes.

    A single object that encapsulates ALL ``dropp_off_point_id`` logic:
    - ``build_segment_condition()`` — how two segments connect
    - ``modify_drop_join()`` — how the drop table is joined
    """

    def __init__(self, drop_off_column: str = "dropp_off_point_id") -> None:
        self._drop_off_column = drop_off_column

    def build_segment_condition(self, from_alias: object, to_alias: object) -> BinaryExpression:
        col = getattr(from_alias, self._drop_off_column)  # type: ignore[attr-defined]
        return and_(
            from_alias.end_point_id == to_alias.start_point_id,  # type: ignore[attr-defined]
            or_(
                col.is_(None),
                col == to_alias.end_point_id,  # type: ignore[attr-defined]
            ),
        )

    def modify_drop_join(
        self,
        from_alias: object,
        drop_alias: object,
        rules_cond: BinaryExpression,
    ) -> tuple[BinaryExpression, BinaryExpression]:
        col = getattr(from_alias, self._drop_off_column)  # type: ignore[attr-defined]
        return (
            and_(col.is_(None), rules_cond),
            or_(
                col.isnot(None),  # type: ignore[attr-defined]
                drop_alias.id.isnot(None),  # type: ignore[attr-defined]
            ),
        )
