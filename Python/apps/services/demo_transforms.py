from collections.abc import Iterable
from contextlib import suppress

from services.group_points import GroupedPointWithPort
from shared.context import ContextKind, get_context
from shared.dto.route import RouteResult, RouteSegment

from .profit import apply_demo_profit_to_route


def strip_demo_fields(segments: Iterable[RouteSegment], excluded_fields: Iterable[str]) -> None:
    """Hide the fields the caller must not see."""
    for segment in segments:
        for field in excluded_fields:
            with suppress(ValueError):
                setattr(segment, field, None)


def strip_demo_fields_from_points(data: list[GroupedPointWithPort]) -> None:
    """Hide the companies of the points from a demo guest."""
    context = get_context()
    if context.kind != ContextKind.DEMO:
        return

    if "company" not in context.excluded_fields:
        return

    for point in data:
        point.companies = []
        for port in point.ports:
            port.companies = []


async def apply_demo_transforms(route: RouteResult) -> None:
    """Apply the demo rules to a calculated route."""
    context = get_context()
    if context.kind != ContextKind.DEMO:
        return

    if context.sea_profit or context.rail_profit:
        await apply_demo_profit_to_route(
            route,
            context.sea_profit,
            context.sea_profit_currency,
            context.rail_profit,
            context.rail_profit_currency,
        )

    strip_demo_fields(route.segments, context.excluded_fields)
