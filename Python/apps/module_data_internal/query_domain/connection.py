from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from module_data_internal.query_domain.connection_rules import ConnectionRule
from sqlalchemy import BinaryExpression, and_

if TYPE_CHECKING:
    from module_data_internal.query_domain.drop import DropConnection


@dataclass
class RouteSegmentConnection:
    """Connection between two route segments."""

    from_seg: object
    to_seg: object
    drops: list[DropConnection] = field(default_factory=list)
    _rules: list[ConnectionRule] = field(default_factory=list)
    _drop_aware_bridge: object | None = None

    def rule(self, rule: ConnectionRule) -> RouteSegmentConnection:
        self._rules.append(rule)
        return self

    def with_drop(self, drop: DropConnection) -> RouteSegmentConnection:
        self.drops.append(drop)
        return self

    def with_drop_aware_bridge(self, bridge: object) -> RouteSegmentConnection:
        self._drop_aware_bridge = bridge
        return self

    def build_condition(self, from_alias: object, to_alias: object) -> BinaryExpression:
        conditions = [rule.to_sql(from_alias, to_alias) for rule in self._rules]
        if self._drop_aware_bridge is not None:
            bridge_cond = self._drop_aware_bridge.build_segment_condition(  # type: ignore[attr-defined]
                from_alias, to_alias,
            )
            conditions.append(bridge_cond)
        return and_(*conditions)
