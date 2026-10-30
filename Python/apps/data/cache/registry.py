import logging
from functools import cache

from shared.cache import (
    CacheBackend,
    CacheEntity,
    CachePolicy,
    CacheStorage,
    RedisStorage,
    cache_prefix,
    is_multi_source,
)
from shared.database import get_database
from shared.orm.cache_policy import CachePolicyModel
from sqlalchemy import select

logger = logging.getLogger(__name__)


class CacheRegistry:
    """Builds the cache backends of the entities from the policies in the database.

    Policies are read from the database at startup. An entity without a
    policy row is not cached, so a source that was never configured simply
    does not use the cache.

    For multi-source entities (departures, destinations, containers, routes,
    points) source is required in the policy. For single-source entities
    (rates, settings) source is None — the entity itself identifies the
    source.
    """

    def __init__(self, storage: CacheStorage | None = None) -> None:
        self._storage = storage or RedisStorage()
        self._policies: dict[CacheEntity, dict[str | None, CachePolicy]] = {}
        self._backends: dict[tuple[CacheEntity, str | None], CacheBackend] = {}
        self._loaded = False

    async def load(self) -> bool:
        """Read the policies from the database.

        Returns True when the policies changed and the built backends were
        dropped. ``False`` means the database still holds the same policies,
        so the backends are left untouched and pending cache writes survive
        a periodic refresh.
        """
        async with get_database().session_context() as session:
            result = await session.execute(select(CachePolicyModel))
            models = list(result.scalars().all())

        policies: dict[CacheEntity, dict[str | None, CachePolicy]] = {}
        ignored: list[str] = []
        for model in models:
            try:
                entity = CacheEntity(model.entity)
            except ValueError:
                ignored.append(f"Unknown cache entity {model.entity!r} of source {model.source!r}, ignored")
                continue
            source = model.source
            if is_multi_source(entity) and not source:
                ignored.append(f"Entity {entity!r} requires a source, got {source!r}, ignored")
                continue
            if not is_multi_source(entity) and source:
                ignored.append(f"Entity {entity!r} is single-source, got source {source!r}, ignored")
                continue
            policies.setdefault(entity, {})[source] = CachePolicy(
                source=source,
                entity=entity,
                enabled=model.enabled,
                ttl=model.ttl,
            )

        if self._loaded and policies == self._policies:
            return False

        for message in ignored:
            logger.warning("%s", message)

        self._policies = policies
        self._backends = {}
        self._loaded = True
        logger.info("Loaded cache policies for %d entity(ies)", len(policies))
        return True

    def backend(self, entity: CacheEntity, source: str | None = None) -> CacheBackend:
        """The backend of an entity, built with the policies that are loaded."""
        cache_key = (entity, source)
        backend = self._backends.get(cache_key)
        if backend is None:
            policies_for_entity = self._policies.get(entity, {})
            policy = policies_for_entity.get(source)
            backend = CacheBackend(
                self._storage, entity, {entity: policy} if policy is not None else {}
            )
            self._backends[cache_key] = backend
        return backend

    def sources(self) -> list[str]:
        """All sources that have at least one policy."""
        sources: set[str] = set()
        for entity_policies in self._policies.values():
            for source in entity_policies:
                if source is not None:
                    sources.add(source)
        return sorted(sources)

    def policies(self, source: str) -> dict[CacheEntity, CachePolicy]:
        """All policies of a source, keyed by entity."""
        result: dict[CacheEntity, CachePolicy] = {}
        for entity, source_policies in self._policies.items():
            policy = source_policies.get(source)
            if policy is not None:
                result[entity] = policy
        return result

    async def flush(self, source: str) -> int:
        """Remove every cached value of a source, return how many deleted."""
        from shared.cache.storage.redis import RedisStorage

        if not isinstance(self._storage, RedisStorage):
            return 0
        total = 0
        for entity in self._policies:
            policy = self._policies[entity].get(source)
            if policy is None:
                continue
            prefix = cache_prefix(entity, source)
            keys = await self._storage.keys(prefix, limit=10000)
            total += len(keys)
            for key in keys:
                await self._storage.delete(key)
        return total

    async def save_policy(self, source: str, entity: str, *, enabled: bool, ttl: int) -> None:
        """Store (upsert) the policy of an entity of a source."""
        entity_enum = CacheEntity(entity)
        policy = CachePolicy(source=source, entity=entity_enum, enabled=enabled, ttl=ttl)
        self._policies.setdefault(entity_enum, {})[source] = policy
        async with get_database().session_context() as session:
            result = await session.execute(
                select(CachePolicyModel).where(
                    CachePolicyModel.source == source,
                    CachePolicyModel.entity == entity,
                ),
            )
            model = result.scalar_one_or_none()
            if model is None:
                session.add(
                    CachePolicyModel(
                        source=source,
                        entity=entity,
                        enabled=enabled,
                        ttl=ttl,
                    ),
                )
            else:
                model.enabled = enabled
                model.ttl = ttl
            await session.flush()

    async def remove_policies(self, source: str) -> int:
        """Remove all policies of a source, return how many removed."""
        count = 0
        for entity in list(self._policies.keys()):
            if source in self._policies[entity]:
                del self._policies[entity][source]
                count += 1
        async with get_database().session_context() as session:
            await session.execute(
                CachePolicyModel.__table__.delete().where(CachePolicyModel.source == source)
            )
            await session.flush()
        return count


@cache
def get_cache_registry() -> CacheRegistry:
    return CacheRegistry()
