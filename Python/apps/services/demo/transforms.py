from collections.abc import Iterable
from contextlib import suppress

from data.settings.cached import get_setting_cached
from entrypoints.user.dependencies.auth_context import AuthContext
from services.demo.profit import apply_demo_profit_to_route
from shared.models.route_entities import RouteResult, RouteSegment


def strip_demo_fields(segments: list[RouteSegment], excluded_fields: Iterable[str] | None = None) -> None:
    """Set every configured field to None on the given segments (demo blurring)."""
    if not excluded_fields:
        return

    for segment in segments:
        for field in excluded_fields:
            with suppress(ValueError):
                setattr(segment, field, None)


async def apply_demo_transforms_to_route(route: RouteResult, auth: AuthContext) -> None:
    """Apply demo profit and field stripping to a single route.

    No-op for non-demo contexts.
    """
    if not auth.is_demo:
        return

    if auth.sea_profit or auth.rail_profit:
        await apply_demo_profit_to_route(
            route,
            auth.sea_profit,
            auth.sea_profit_currency,
            auth.rail_profit,
            auth.rail_profit_currency,
        )

    setting = await get_setting_cached("feature-flag", "demo-excluded-fields")
    excluded_fields = setting.value if setting and isinstance(setting.value, list) else []
    strip_demo_fields(route.segments, excluded_fields)
