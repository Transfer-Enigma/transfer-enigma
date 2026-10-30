import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from services.cache.registry import get_cache_registry
from shared.config import get_settings

logger = logging.getLogger(__name__)


async def refresh_policies(interval: int) -> None:
    """Reload cache policies from the database every ``interval`` seconds."""
    registry = get_cache_registry()
    while True:
        await asyncio.sleep(interval)
        try:
            await registry.load()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to refresh cache policies")


def start_policy_refresh() -> asyncio.Task | None:
    """Start the periodic cache policy refresh, if it is enabled."""
    interval = get_settings().CACHE_POLICIES_REFRESH_INTERVAL_SECONDS
    if interval <= 0:
        logger.info("Periodic cache policy refresh is disabled")
        return None
    logger.info("Refreshing cache policies every %d seconds", interval)
    return asyncio.create_task(refresh_policies(interval), name="cache-policies-refresh")


@asynccontextmanager
async def policy_refresh() -> AsyncIterator[None]:
    """Keep the cache policies up to date for the duration of the context."""
    task = start_policy_refresh()
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
