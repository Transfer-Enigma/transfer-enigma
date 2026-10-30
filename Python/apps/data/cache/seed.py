"""Unified seeding of cache defaults: settings and cache policies.

Single entry point used both by the service lifespans and by the one-shot
``dbseeder`` container (``python -m data.cache.seed``). Every ensure function
is idempotent: it only creates rows that are still missing.
"""

import asyncio
import logging

from shared.database import get_database
from shared.redis_client import get_redis_client

from .cache_policies import ensure_cache_policies
from .registry import get_cache_registry
from .settings import create_default_settings

logger = logging.getLogger(__name__)


async def ensure_all() -> None:
    """Create all missing cache defaults: settings, then cache policies."""
    await create_default_settings()
    await ensure_cache_policies()


async def _main() -> None:
    await get_database().init()
    await get_redis_client().init()
    await get_cache_registry().load()
    try:
        await ensure_all()
    finally:
        await get_database().close()
        await get_redis_client().close()
    logger.info("Seeding finished successfully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
