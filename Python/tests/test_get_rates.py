import asyncio
import datetime
from unittest.mock import patch

import pytest
from data.cache.registry import CacheRegistry
from services.get_rates import RATES_CACHE_PART, _set_rates_cache, get_rates
from shared.cache import CacheEntity, CachePolicy, LocalStorage


class MockCurrency:
    def __init__(self, code, value):
        self.code = code
        self.value = value


class MockExchangeRates:
    def __init__(self, _date):
        self.rates = [
            MockCurrency("USD", 90.0),
            MockCurrency("EUR", 100.0),
            MockCurrency("CNY", 12.5),
        ]


def _registry(*, enabled=True, ttl=60) -> CacheRegistry:
    """A registry with the rates policy of the CBR source."""
    registry = CacheRegistry(storage=LocalStorage())
    registry.add_policies([
        CachePolicy(source=None, entity=CacheEntity.RATES, enabled=enabled, ttl=ttl),
    ])
    return registry


@pytest.mark.asyncio
async def test_get_rates_returns_tuple():
    registry = _registry()
    with (
        patch("services.get_rates.ExchangeRates", return_value=MockExchangeRates(None)),
        patch("services.get_rates.get_cache_registry", return_value=registry),
    ):
        rates, dt = await get_rates()

    assert isinstance(rates, dict)
    assert rates["USD"] == 90.0
    assert rates["EUR"] == 100.0
    assert rates["RUB"] == 1.0
    assert rates["RUR"] == 1.0
    assert dt == datetime.date.today()


@pytest.mark.asyncio
async def test_get_rates_with_passed_datetime():
    dt = datetime.datetime(2024, 6, 15, 12, 0, 0)
    registry = _registry()
    with (
        patch("services.get_rates.ExchangeRates", return_value=MockExchangeRates(None)),
        patch("services.get_rates.get_cache_registry", return_value=registry),
    ):
        rates, updated_at = await get_rates(dt)

    assert isinstance(rates, dict)
    assert updated_at == datetime.date(2024, 6, 15)


@pytest.mark.asyncio
async def test_get_rates_api_failure_fallback_to_cache():
    registry = _registry()
    await registry.backend(CacheEntity.RATES).set(
        RATES_CACHE_PART,
        data={"rates": {"USD": 85.0}, "date": "2024-06-14"},
        dump=True,
    )
    with (
        patch("services.get_rates.ExchangeRates", side_effect=ConnectionError("API unavailable")),
        patch("services.get_rates.get_cache_registry", return_value=registry),
    ):
        rates, cached_date = await get_rates(datetime.datetime(2020, 1, 1))

    assert rates["USD"] == 85.0
    assert cached_date == datetime.date(2024, 6, 14)


@pytest.mark.asyncio
async def test_get_rates_api_failure_no_cache_raises():
    registry = _registry()
    with (
        patch("services.get_rates.ExchangeRates", side_effect=ConnectionError("API unavailable")),
        patch("services.get_rates.get_cache_registry", return_value=registry),
        pytest.raises(RuntimeError, match="No rates available"),
    ):
        await get_rates(datetime.datetime(2020, 1, 1))


@pytest.mark.asyncio
async def test_get_rates_without_a_policy_does_not_raise():
    """Without a policy row the entity is not cached, the API is the only source."""
    registry = CacheRegistry(storage=LocalStorage())
    with (
        patch("services.get_rates.ExchangeRates", side_effect=ConnectionError("API unavailable")),
        patch("services.get_rates.get_cache_registry", return_value=registry),
        pytest.raises(RuntimeError, match="No rates available"),
    ):
        await get_rates(datetime.datetime(2020, 1, 1))


@pytest.mark.asyncio
async def test_set_rates_cache_stores_the_rates_and_the_date():
    registry = _registry()
    with patch("services.get_rates.get_cache_registry", return_value=registry):
        await _set_rates_cache({"USD": 90.0}, datetime.date(2024, 6, 15))

    cached = await registry.backend(CacheEntity.RATES).get(RATES_CACHE_PART)
    assert cached == {"rates": {"USD": 90.0}, "date": "2024-06-15"}


@pytest.mark.asyncio
async def test_get_rates_caches_the_rates():
    registry = _registry()
    with (
        patch("services.get_rates.ExchangeRates", return_value=MockExchangeRates(None)),
        patch("services.get_rates.get_cache_registry", return_value=registry),
    ):
        await get_rates(datetime.datetime(2024, 6, 15, 12, 0, 0))

        cached = None
        for _ in range(50):
            cached = await registry.backend(CacheEntity.RATES).get(RATES_CACHE_PART)
            if cached is not None:
                break
            await asyncio.sleep(0.01)

    assert cached is not None
    assert cached["rates"]["USD"] == 90.0
    assert cached["date"] == "2024-06-15"
