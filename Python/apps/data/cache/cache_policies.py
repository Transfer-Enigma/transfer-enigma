"""Cache policy data layer.

Creates default cache policies that are still missing.
Existing rows are never touched.
"""

import logging

from shared.cache import CacheEntity
from shared.cache_policy_definitions import get_cache_policy_definitions
from shared.database import Base, get_database
from shared.orm.cache_policy import CachePolicyModel
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def ensure_cache_policies() -> None:
    """Create cache policies that are still missing.

    Existing rows are left untouched: policies are admin-managed,
    the seeder only fills the gaps. Idempotent.
    """
    definitions = get_cache_policy_definitions()
    async with get_database().session_context() as session:
        conn = await session.connection()
        await conn.run_sync(Base.metadata.create_all)
        for defn in definitions:
            try:
                CacheEntity(defn.entity)
            except ValueError:
                logger.error("Unknown cache entity in definitions: %r, skipping", defn.entity)
                continue
            result = await session.execute(
                select(CachePolicyModel).where(
                    CachePolicyModel.source == defn.source,
                    CachePolicyModel.entity == defn.entity,
                ),
            )
            if result.scalar_one_or_none() is not None:
                continue
            session.add(
                CachePolicyModel(
                    source=defn.source,
                    entity=defn.entity,
                    enabled=defn.enabled,
                    ttl=defn.ttl,
                )
            )
            await session.flush()
            logger.info(
                "Created default cache policy: %s:%s enabled=%s ttl=%s",
                defn.source,
                defn.entity,
                defn.enabled,
                defn.ttl,
            )
