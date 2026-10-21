import logging
from functools import cache

from shared.cache import (
    CacheBackend,
    CacheEntity,
    CachePolicy,
    CacheStorage,
    RedisStorage,
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

    async def load(self) -> None:
        """Read the policies from the database and drop the built backends."""
        async with get_database().session_context() as session:
            result = await session.execute(select(CachePolicyModel))
            models = list(result.scalars().all())

        policies: dict[CacheEntity, dict[str | None, CachePolicy]] = {}
        for model in models:
            try:
                entity = CacheEntity(model.entity)
            except ValueError:
                logger.warning("Unknown cache entity %r of source %r, ignored", model.entity, model.source)
                continue
            source = model.source
            if is_multi_source(entity) and not source:
                logger.warning(
                    "Entity %r requires a source, got %r, ignored", entity, source
                )
                continue
            if not is_multi_source(entity) and source:
                logger.warning(
                    "Entity %r is single-source, got source %r, ignored", entity, source
                )
                continue
            policies.setdefault(entity, {})[source] = CachePolicy(
                source=source,
                entity=entity,
                enabled=model.enabled,
                ttl=model.ttl,
            )

        self._policies = policies
        self._backends = {}
        logger.info("Loaded cache policies for %d entity(ies)", len(policies))

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


@cache
def get_cache_registry() -> CacheRegistry:
    return CacheRegistry()
