import datetime
from unittest.mock import patch

import pytest
from services.profit import (
    _apply_profit_to_segments,
    _convert_currency,
    _get_converted_profit,
    apply_demo_profit_to_route,
)
from shared.dto.route import PriceItem, RouteResult, RouteSegment

_CB_RATES = {"USD": 90.0, "RUB": 1.0, "EUR": 100.0}


class TestConvertCurrency:
    def test_same_currency_returns_original(self):
        result = _convert_currency(100.0, "USD", "USD", _CB_RATES)
        assert result == 100.0

    def test_zero_amount_returns_zero(self):
        result = _convert_currency(0.0, "USD", "RUB", _CB_RATES)
        assert result == 0.0

    def test_conversion_uses_rates(self):
        result = _convert_currency(100.0, "USD", "RUB", _CB_RATES)
        assert result == 9000.0

    def test_conversion_reverse(self):
        result = _convert_currency(9000.0, "RUB", "USD", _CB_RATES)
        assert result == 100.0

    def test_missing_rate_returns_original(self):
        result = _convert_currency(100.0, "USD", "GBP", _CB_RATES)
        assert result == 100.0


class TestGetConvertedProfit:
    def test_returns_rounded_profit(self):
        result = _get_converted_profit(100.0, "USD", "RUB", _CB_RATES)
        assert result == 9000.0

    def test_rounds_to_two_decimals(self):
        result = _get_converted_profit(100.37, "USD", "RUB", _CB_RATES)
        assert result == round(100.37 * 90.0 / 1.0, 2)


class TestApplyDemoProfitToRoute:
    async def _apply(self, route, **kwargs):
        with patch("services.profit.get_rates", return_value=(_CB_RATES, datetime.date.today())):
            await apply_demo_profit_to_route(route, **kwargs)

    def _segment_price(self, route, segment_index=0, price_index=0):
        return route.segments[segment_index].prices[price_index].value

    @pytest.mark.asyncio
    async def test_sea_profit_added_to_sea_segment(self):
        route = RouteResult(segments=[_make_segment(seg_type="sea")])
        await self._apply(
            route, sea_profit=50.0, sea_profit_currency="USD", rail_profit=0.0, rail_profit_currency="USD"
        )

        assert self._segment_price(route) == 1050.0

    @pytest.mark.asyncio
    async def test_rail_profit_added_to_rail_segment(self):
        route = RouteResult(segments=[_make_segment(seg_type="rail")])
        await self._apply(
            route, sea_profit=0.0, sea_profit_currency="USD", rail_profit=30.0, rail_profit_currency="USD"
        )

        assert self._segment_price(route) == 1030.0

    @pytest.mark.asyncio
    async def test_no_profit_when_all_zero(self):
        route = RouteResult(segments=[_make_segment(seg_type="sea")])

        await apply_demo_profit_to_route(
            route,
            sea_profit=0.0,
            sea_profit_currency="USD",
            rail_profit=0.0,
            rail_profit_currency="USD",
        )

        assert self._segment_price(route) == 1000.0

    @pytest.mark.asyncio
    async def test_sea_profit_not_added_to_rail_segment(self):
        route = RouteResult(segments=[_make_segment(seg_type="rail")])
        await self._apply(
            route, sea_profit=50.0, sea_profit_currency="USD", rail_profit=0.0, rail_profit_currency="USD"
        )

        assert self._segment_price(route) == 1000.0

    @pytest.mark.asyncio
    async def test_unknown_segment_type_skipped(self):
        route = RouteResult(segments=[_make_segment(seg_type="truck")])
        await self._apply(
            route, sea_profit=50.0, sea_profit_currency="USD", rail_profit=30.0, rail_profit_currency="USD"
        )

        assert self._segment_price(route) == 1000.0

    @pytest.mark.asyncio
    async def test_mixed_segments(self):
        segments = [
            _make_segment(seg_type="sea"),
            _make_segment(seg_type="rail", price_value=500.0),
        ]
        route = RouteResult(segments=segments)

        await self._apply(
            route, sea_profit=100.0, sea_profit_currency="USD", rail_profit=50.0, rail_profit_currency="USD"
        )

        assert segments[0].prices[0].value == 1100.0
        assert segments[1].prices[0].value == 550.0

    @pytest.mark.asyncio
    async def test_currency_conversion(self):
        segment = _make_segment(seg_type="sea", price_value=1000.0, currency="RUB")
        route = RouteResult(segments=[segment])

        await self._apply(
            route, sea_profit=100.0, sea_profit_currency="USD", rail_profit=0.0, rail_profit_currency="USD"
        )

        assert segment.prices[0].value == 10000.0


def _make_segment(seg_type="sea", price_value=1000.0, currency="USD") -> RouteSegment:
    return RouteSegment(
        id=1,
        company="Test",
        type=seg_type,
        effectiveFrom="2024-01-01",
        effectiveTo="2025-12-31",
        startPointCountry="RU",
        startPointName="Moscow",
        endPointCountry="CN",
        endPointName="Shanghai",
        prices=[PriceItem(value=price_value, currency=currency, conversation_percents=0)],
    )


@pytest.mark.parametrize(
    "segment_type, expected_value",
    [
        ("sea", 1100.0),
        ("rail", 1050.0),
        ("truck", 1000.0),
    ],
)
def test_various_segment_types_with_profit(segment_type, expected_value):
    segments = [
        RouteSegment(
            id=1,
            company="Test",
            type=segment_type,
            effectiveFrom="2024-01-01",
            effectiveTo="2025-12-31",
            startPointCountry="RU",
            startPointName="Moscow",
            endPointCountry="CN",
            endPointName="Shanghai",
            prices=[PriceItem(value=1000.0, currency="USD", conversation_percents=0)],
        ),
    ]

    _apply_profit_to_segments(
        segments,
        sea_profit=100.0,
        sea_profit_currency="USD",
        rail_profit=50.0,
        rail_profit_currency="USD",
        rates=_CB_RATES,
    )

    assert segments[0].prices[0].value == expected_value
