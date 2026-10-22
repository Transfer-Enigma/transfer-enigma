import pytest
from shared.identifiers import ExternalId, InternalId, SourceKind


def test_internal_id_equality_by_hash():
    assert InternalId(1) == InternalId(1)
    assert InternalId(1) != InternalId(2)
    assert hash(InternalId(1)) == hash(InternalId(1))


def test_external_id_equality_by_hash():
    assert ExternalId("a") == ExternalId("a")
    assert ExternalId("a") != ExternalId("b")
    assert hash(ExternalId("a")) == hash(ExternalId("a"))


def test_internal_and_external_not_equal():
    assert InternalId(1) != ExternalId("1")
    assert hash(InternalId(1)) != hash(ExternalId("1"))


def test_source_kind():
    assert InternalId(1).source == SourceKind.INTERNAL
    assert ExternalId("x").source == SourceKind.EXTERNAL


def test_str():
    assert str(InternalId(5)) == "5"
    assert str(ExternalId("x")) == "x"


def test_identifiers_are_hashable():
    assert {InternalId(1), InternalId(2), InternalId(1)} == {InternalId(1), InternalId(2)}
    assert {ExternalId("a"), ExternalId("b"), ExternalId("a")} == {ExternalId("a"), ExternalId("b")}


@pytest.mark.parametrize(
    "identifier,expected",
    [
        (InternalId(1), "1"),
        (ExternalId("x"), "x"),
    ],
)
def test_str_parametrized(identifier, expected):
    assert str(identifier) == expected
