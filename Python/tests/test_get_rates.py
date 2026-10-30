import asyncio
import datetime
from unittest.mock import patch

import pytest
from data.cache.storage import LocalStorage
from services.cache.registry import CacheRegistry
from services.rates.get import RATES_CACHE_PART, _set_rates_cache, get_rates
from shared.dto.cache import CacheEntity
from shared.orm.cache_policy import CachePolicyModel


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


async def _registry(sqlite_db, sqlite_session, *, enabled=True, ttl=60) -> CacheRegistry:
    """A registry with the rates policy of the CBR source stored in the database."""
    sqlite_session.add(
        CachePolicyModel(
            source=None,
            entity=CacheEntity.RATES.value,
            enabled=enabled,
            ttl=ttl,
        ),
    )
    await sqlite_session.commit()

    registry = CacheRegistry(storage=LocalStorage())
    with patch("services.cache.registry.get_database", return_value=sqlite_db):
        await registry.load()
    return registry


@pytest.mark.asyncio
async def test_get_rates_returns_tuple(sqlite_db, sqlite_session):
    registry = await _registry(sqlite_db, sqlite_session)
    with (
        patch("services.rates.get.ExchangeRates", return_value=MockExchangeRates(None)),
        patch("services.rates.get.get_cache_registry", return_value=registry),
    ):
        rates, dt = await get_rates()

    assert isinstance(rates, dict)
    assert rates["USD"] == 90.0
    assert rates["EUR"] == 100.0
    assert rates["RUB"] == 1.0
    assert rates["RUR"] == 1.0
    assert dt == datetime.date.today()


@pytest.mark.asyncio
async def test_get_rates_with_passed_datetime(sqlite_db, sqlite_session):
    dt = datetime.datetime(2024, 6, 15, 12, 0, 0)
    registry = await _registry(sqlite_db, sqlite_session)
    with (
        patch("services.rates.get.ExchangeRates", return_value=MockExchangeRates(None)),
        patch("services.rates.get.get_cache_registry", return_value=registry),
    ):
        rates, updated_at = await get_rates(dt)

    assert isinstance(rates, dict)
    assert updated_at == datetime.date(2024, 6, 15)


@pytest.mark.asyncio
async def test_get_rates_api_failure_fallback_to_cache(sqlite_db, sqlite_session):
    registry = await _registry(sqlite_db, sqlite_session)
    await registry.backend(CacheEntity.RATES).set(
        RATES_CACHE_PART,
        data={"rates": {"USD": 85.0}, "date": "2024-06-14"},
        dump=True,
    )
    with (
        patch("services.rates.get.ExchangeRates", side_effect=ConnectionError("API unavailable")),
        patch("services.rates.get.get_cache_registry", return_value=registry),
    ):
        rates, cached_date = await get_rates(datetime.datetime(2020, 1, 1))

    assert rates["USD"] == 85.0
    assert cached_date == datetime.date(2024, 6, 14)


@pytest.mark.asyncio
async def test_get_rates_api_failure_no_cache_raises(sqlite_db, sqlite_session):
    registry = await _registry(sqlite_db, sqlite_session)
    with (
        patch("services.rates.get.ExchangeRates", side_effect=ConnectionError("API unavailable")),
        patch("services.rates.get.get_cache_registry", return_value=registry),
        pytest.raises(RuntimeError, match="No rates available"),
    ):
        await get_rates(datetime.datetime(2020, 1, 1))


@pytest.mark.asyncio
async def test_get_rates_without_a_policy_does_not_raise():
    """Without a policy row the entity is not cached, the API is the only source."""
    registry = CacheRegistry(storage=LocalStorage())
    with (
        patch("services.rates.get.ExchangeRates", side_effect=ConnectionError("API unavailable")),
        patch("services.rates.get.get_cache_registry", return_value=registry),
        pytest.raises(RuntimeError, match="No rates available"),
    ):
        await get_rates(datetime.datetime(2020, 1, 1))


@pytest.mark.asyncio
async def test_set_rates_cache_stores_the_rates_and_the_date(sqlite_db, sqlite_session):
    registry = await _registry(sqlite_db, sqlite_session)
    with patch("services.rates.get.get_cache_registry", return_value=registry):
        await _set_rates_cache({"USD": 90.0}, datetime.date(2024, 6, 15))

    cached = await registry.backend(CacheEntity.RATES).get(RATES_CACHE_PART)
    assert cached == {"rates": {"USD": 90.0}, "date": "2024-06-15"}


@pytest.mark.asyncio
async def test_get_rates_caches_the_rates(sqlite_db, sqlite_session):
    registry = await _registry(sqlite_db, sqlite_session)
    with (
        patch("services.rates.get.ExchangeRates", return_value=MockExchangeRates(None)),
        patch("services.rates.get.get_cache_registry", return_value=registry),
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
