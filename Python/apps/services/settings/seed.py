"""Settings seed service.

Creates default settings that are still missing.
"""

import logging

from data.cache.settings import create_default_settings

logger = logging.getLogger(__name__)


async def do_seed() -> None:
    """Create missing default settings."""
    await create_default_settings()
