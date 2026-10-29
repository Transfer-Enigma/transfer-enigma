"""One-shot seed entrypoint.

Thin entrypoint that triggers all seed services:
- cache policies via services.cache.seed
- settings via services.settings.seed

Run as: python -m entrypoints.seed.main
"""

import asyncio
import logging

from services.cache.seed import do_seed as seed_cache_policies
from services.settings.seed import do_seed as seed_settings

logger = logging.getLogger(__name__)


async def main() -> None:
    await seed_cache_policies()
    await seed_settings()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
