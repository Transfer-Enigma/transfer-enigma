from typing import Any, TypedDict


class PointItem(TypedDict, total=False):
    """A point of a source, in the shape the grouping works with."""

    id: str  # noqa: A003
    company: dict[str, Any]
    ports: list[Any]
    translates: dict[str, dict[str, str]]
