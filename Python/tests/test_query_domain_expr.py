from module_data_internal.query_domain import Segment
from module_data_internal.query_domain.expr import ColumnRef, Condition, Connector


class _MockOwner(Segment):
    pass


def _ref(column: str = "x") -> ColumnRef:
    return ColumnRef(_MockOwner(), column)


class TestColumnRef:
    def test_constructor(self) -> None:
        owner = _MockOwner()
        ref = ColumnRef(owner, "foo")
        assert ref.owner is owner
        assert ref.column_name == "foo"

    def test_equals_returns_eq_condition(self) -> None:
        ref = _ref()
        cond = ref.equals(42)
        assert cond.op == "eq"
        assert cond.left is ref
        assert cond.right == 42

    def test_equals_with_column_ref(self) -> None:
        ref_a = _ref("a")
        ref_b = _ref("b")
        cond = ref_a.equals(ref_b)
        assert cond.op == "eq"
        assert cond.left is ref_a
        assert cond.right is ref_b

    def test_in_(self) -> None:
        ref = _ref()
        cond = ref.in_([1, 2, 3])
        assert cond.op == "in"
        assert cond.left is ref
        assert cond.right == [1, 2, 3]

    def test_lte(self) -> None:
        ref = _ref()
        cond = ref.lte(100)
        assert cond.op == "lte"
        assert cond.left is ref
        assert cond.right == 100

    def test_gte(self) -> None:
        ref = _ref()
        cond = ref.gte(50)
        assert cond.op == "gte"
        assert cond.left is ref
        assert cond.right == 50


class TestCondition:
    def test_condition_holds_attributes(self) -> None:
        ref = _ref()
        cond = Condition("eq", left=ref, right="b")
        assert cond.op == "eq"
        assert cond.left is ref
        assert cond.right == "b"
        assert cond.operand is None
        assert cond.operands is None

    def test_condition_unary(self) -> None:
        ref = _ref()
        cond = Condition("is_not_null", operand=ref)
        assert cond.operand is ref
        assert cond.left is None

    def test_condition_nary(self) -> None:
        ref = _ref()
        c1 = Condition("eq", left=ref, right=1)
        c2 = Condition("eq", left=ref, right=2)
        cond = Condition("and", operands=[c1, c2])
        assert cond.operands == [c1, c2]


class TestConnector:
    def test_and_(self) -> None:
        c1 = _ref("a").equals(1)
        c2 = _ref("b").equals(2)
        result = Connector.and_(c1, c2)
        assert result.op == "and"
        assert result.operands == [c1, c2]

    def test_and_single(self) -> None:
        c1 = _ref("a").equals(1)
        result = Connector.and_(c1)
        assert result.op == "and"
        assert result.operands == [c1]

    def test_and_none(self) -> None:
        result = Connector.and_()
        assert result.op == "and"
        assert result.operands == []

    def test_or_(self) -> None:
        c1 = _ref("a").equals(1)
        c2 = _ref("b").equals(2)
        result = Connector.or_(c1, c2)
        assert result.op == "or"
        assert result.operands == [c1, c2]

    def test_or_single(self) -> None:
        c1 = _ref("a").equals(1)
        result = Connector.or_(c1)
        assert result.op == "or"
        assert result.operands == [c1]
