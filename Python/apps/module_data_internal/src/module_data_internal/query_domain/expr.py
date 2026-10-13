from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .drop_off import DropOff
    from .segment import Segment


class PriceRef:
    def __init__(self, segment: Segment) -> None:
        self.segment = segment

    @property
    def container(self) -> ColumnRef:
        return ColumnRef(self, "container_id")


class ColumnRef:
    def __init__(self, owner: Segment | DropOff | PriceRef, column_name: str) -> None:
        self.owner = owner
        self.column_name = column_name

    def equals(self, other: ColumnRef | Any) -> Condition:
        return Condition(op="eq", left=self, right=other)

    def not_(self) -> Condition:
        return Condition(op="not", operand=self)

    def not_equals(self, other: ColumnRef | Any) -> Condition:
        return Condition(op="not", operand=Condition(op="eq", left=self, right=other))

    def not_null(self) -> Condition:
        return Condition(op="is_not_null", operand=self)

    def null(self) -> Condition:
        return Condition(op="is_null", operand=self)

    def in_(self, values: list) -> Condition:
        return Condition(op="in", left=self, right=values)

    def lte(self, value: Any) -> Condition:
        return Condition(op="lte", left=self, right=value)

    def gte(self, value: Any) -> Condition:
        return Condition(op="gte", left=self, right=value)

    def __repr__(self) -> str:
        return f"ColumnRef({self.column_name})"


class Condition:
    def __init__(
        self,
        op: str,
        left: ColumnRef | None = None,
        right: Any = None,
        operand: ColumnRef | Condition | None = None,
        operands: list[Condition] | None = None,
    ) -> None:
        self.op = op
        self.left = left
        self.right = right
        self.operand = operand
        self.operands = operands


class Connector:
    @staticmethod
    def and_(*conditions: Condition) -> Condition:
        return Condition(op="and", operands=list(conditions))

    @staticmethod
    def or_(*conditions: Condition) -> Condition:
        return Condition(op="or", operands=list(conditions))
