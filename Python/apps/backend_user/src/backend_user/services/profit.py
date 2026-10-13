import logging

from backend_user.schemas.routes import NormalizedRoutes
from backend_user.services.get_rates import get_rates
from module_shared.models.route import RouteResult, RouteSegment

logger = logging.getLogger(__name__)


def _convert_currency(amount: float, from_currency: str, to_currency: str, rates: dict[str, float]) -> float:
    if from_currency == to_currency or not amount:
        return amount
    if from_currency in rates and to_currency in rates:
        return amount * rates[from_currency] / rates[to_currency]
    return amount


def _get_converted_profit(
    profit: float,
    profit_currency: str,
    segment_currency: str,
    rates: dict[str, float],
) -> float:
    converted_profit = _convert_currency(profit, profit_currency, segment_currency, rates)
    return round(converted_profit, 2)


def _apply_profit_to_segments(
    segments: list[RouteSegment],
    sea_profit: float,
    sea_profit_currency: str,
    rail_profit: float,
    rail_profit_currency: str,
    rates: dict[str, float],
) -> None:
    for segment in segments:
        seg_type = (segment.type or "").lower()
        if seg_type == "sea":
            profit = sea_profit
            profit_currency = sea_profit_currency
        elif seg_type == "rail":
            profit = rail_profit
            profit_currency = rail_profit_currency
        else:
            continue

        for price in segment.prices or []:
            segment_currency = price.currency
            converted_profit = _get_converted_profit(profit, profit_currency, segment_currency, rates)
            price.value = float(price.value) + converted_profit


async def apply_demo_profit_to_routes(
    routes: NormalizedRoutes,
    sea_profit: float,
    sea_profit_currency: str,
    rail_profit: float,
    rail_profit_currency: str,
):
    if not sea_profit and not rail_profit:
        return

    logger.info(
        "Applying profit: sea=%.2f %s, rail=%.2f %s",
        sea_profit, sea_profit_currency, rail_profit, rail_profit_currency,
    )
    rates, _ = await get_rates()

    for route in routes:
        _apply_profit_to_segments(route[0], sea_profit, sea_profit_currency, rail_profit, rail_profit_currency, rates)


async def apply_demo_profit_to_route(
    route: RouteResult,
    sea_profit: float,
    sea_profit_currency: str,
    rail_profit: float,
    rail_profit_currency: str,
) -> None:
    if not sea_profit and not rail_profit:
        return

    logger.info(
        "Applying profit to route: sea=%.2f %s, rail=%.2f %s",
        sea_profit, sea_profit_currency, rail_profit, rail_profit_currency,
    )
    rates, _ = await get_rates()

    _apply_profit_to_segments(
        route.segments, sea_profit, sea_profit_currency, rail_profit, rail_profit_currency, rates
    )
