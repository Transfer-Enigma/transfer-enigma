import json
import logging
from collections.abc import Iterable
from functools import cache

from shared.cache import (
    CacheBackend,
    CacheEntity,
    CachePolicy,
    CacheStorage,
    LocalStorage,
    RedisStorage,
    is_multi_source,
)
from shared.database import get_database
from shared.orm.cache_policy import CachePolicyModel
from sqlalchemy import select

logger = logging.getLogger(__name__)

_POLICY_CACHE_PREFIX = "cache:policies:"


class CacheRegistry:
    """Builds the cache backends of the entities from the policies in the database.

    Policies are read from the database at startup and additionally kept in
    the local policy cache, so the cache knows its own policies without
    hitting the database on every backend lookup. An entity without a policy
    row is not cached, so a source that was never configured simply does not
    use the cache.

    For multi-source entities (departures, destinations, containers, routes,
    points) source is required in the policy. For single-source entities
    (rates, settings) source is None — the entity itself identifies the
    source.
    """

    def __init__(self, storage: CacheStorage | None = None) -> None:
        self._storage = storage or RedisStorage()
        self._policy_cache = LocalStorage()
        self._policies: dict[CacheEntity, dict[str | None, CachePolicy]] = {}
        self._backends: dict[tuple[CacheEntity, str | None], CacheBackend] = {}

    async def load(self) -> None:
        """Read the policies from the database, cache them locally, drop the built backends."""
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
        await self._save_policies_cache()
        logger.info("Loaded cache policies for %d entity(ies)", len(policies))

    async def _save_policies_cache(self) -> None:
        """Write the currently loaded policies into the local policy cache."""
        for entity, sources in self._policies.items():
            key = f"{_POLICY_CACHE_PREFIX}{entity.value}"
            payload = json.dumps(
                [
                    {
                        "source": policy.source,
                        "enabled": policy.enabled,
                        "ttl": policy.ttl,
                    }
                    for policy in sources.values()
                ]
            )
            await self._policy_cache.set(key, payload, ttl=None)

    async def invalidate_policies(self, entity: CacheEntity, source: str | None = None) -> None:
        """Drop the policies of an entity (or one source of it) from memory,
        backends and the local cache.

        Called when cache policies are updated in the database, so the next
        backend lookup re-reads the policies from the database on load().
        """
        if source is None:
            self._policies.pop(entity, None)
            keys_to_pop = [k for k in self._backends if k[0] == entity]
            for k in keys_to_pop:
                self._backends.pop(k, None)
            await self._policy_cache.delete(f"{_POLICY_CACHE_PREFIX}{entity.value}")
        else:
            self._policies.get(entity, {}).pop(source, None)
            if not self._policies.get(entity):
                self._policies.pop(entity, None)
            self._backends.pop((entity, source), None)
            await self._policy_cache.delete(f"{_POLICY_CACHE_PREFIX}{entity.value}")

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

    def add_policies(self, policies: Iterable[CachePolicy]) -> None:
        """Add policies to the registry, replacing the ones of the same entity."""
        for policy in policies:
            self._policies.setdefault(policy.entity, {})[policy.source] = policy
            keys_to_pop = [k for k in self._backends if k[0] == policy.entity]
            for k in keys_to_pop:
                self._backends.pop(k, None)

    def policies(self, entity: CacheEntity) -> dict[str | None, CachePolicy]:
        """The policies of an entity."""
        return dict(self._policies.get(entity, {}))

    def entities(self) -> list[CacheEntity]:
        """The entities that have at least one policy."""
        return sorted(self._policies)


@cache
def get_cache_registry() -> CacheRegistry:
    return CacheRegistry()
