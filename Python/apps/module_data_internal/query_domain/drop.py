import datetime
from dataclasses import dataclass, field

from module_data_internal.query_domain.drop_rules import DropRule
from sqlalchemy import BinaryExpression, and_


@dataclass
class DropConnection:
    """Drop-off connection definition.

    Args:
        bridge: Optional drop-aware bridge (e.g. ``DropAwareConnection``).
            When set, ``build_join()`` delegates to ``bridge.modify_drop_join()``.
        required: If ``True``, the drop must match for the row to appear.
    """

    bridge: object | None = None
    required: bool = False
    _rules: list[DropRule] = field(default_factory=list)

    def rule(self, rule: DropRule) -> DropConnection:
        self._rules.append(rule)
        return self

    def build_condition(
        self,
        from_alias: object,
        to_alias: object,
        drop_alias: object,
        from_price_alias: object,
        to_price_alias: object,
        date: datetime.date,
    ) -> BinaryExpression:
        conditions = [
            rule.to_sql(from_alias, to_alias, drop_alias, from_price_alias, to_price_alias, date)
            for rule in self._rules
        ]
        return and_(*conditions)

    def build_join(
        self,
        from_alias: object,
        drop_alias: object,
        join_cond: BinaryExpression,
    ) -> tuple[BinaryExpression, BinaryExpression | None]:
        """Build the final JOIN ON and optional WHERE conditions.

        When a bridge is set, delegates to ``bridge.modify_drop_join()``.
        Otherwise returns the join condition as-is.
        """
        if self.bridge is not None:
            return self.bridge.modify_drop_join(from_alias, drop_alias, join_cond)  # type: ignore[attr-defined]
        return join_cond, None
