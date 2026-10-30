"""One-shot initializer entrypoint.

Runs the data initialization steps when the system starts:
- cache policies via services.cache.seed

Run as: python -m entrypoints.initializer.main
"""

import asyncio
import logging

from services.cache.seed import do_seed as seed_cache_policies

logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the initialization steps."""
    await seed_cache_policies()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
