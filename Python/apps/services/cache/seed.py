"""Cache policy seed service.

Creates default cache policies that are still missing.
"""

import logging

from data.cache.cache_policies import ensure_cache_policies

logger = logging.getLogger(__name__)


async def do_seed() -> None:
    """Create missing default cache policies."""
    await ensure_cache_policies()
