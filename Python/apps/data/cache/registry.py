import logging
from collections.abc import Iterable
from functools import cache

from data.repositories import cache_policies
from shared.cache import CacheBackend, CacheEntity, CachePolicy, CacheStorage, RedisStorage
from shared.context import ContextKind, permissions
from shared.database import get_database

logger = logging.getLogger(__name__)


class CacheRegistry:
    """Builds the cache backends of the sources from the policies in the database.

    An entity without a policy row is not cached, so a source that was
    never configured simply does not use the cache.
    """

    def __init__(self, storage: CacheStorage | None = None) -> None:
        self._storage = storage or RedisStorage()
        self._policies: dict[str, dict[CacheEntity, CachePolicy]] = {}
        self._backends: dict[str, CacheBackend] = {}

    async def load(self) -> None:
        """Read the policies from the database and drop the built backends."""
        async with get_database().session_context() as session:
            models = await cache_policies.list_policies(session)

        policies: dict[str, dict[CacheEntity, CachePolicy]] = {}
        for model in models:
            try:
                entity = CacheEntity(model.entity)
            except ValueError:
                logger.warning("Unknown cache entity %r of source %r, ignored", model.entity, model.source)
                continue
            policies.setdefault(model.source, {})[entity] = CachePolicy(
                source=model.source,
                entity=entity,
                enabled=model.enabled,
                ttl=model.ttl,
            )

        self._policies = policies
        self._backends = {}
        logger.info("Loaded cache policies for %d source(s)", len(policies))

    def backend(self, source: str) -> CacheBackend:
        """The backend of a source, built with the policies that are loaded."""
        backend = self._backends.get(source)
        if backend is None:
            backend = CacheBackend(self._storage, source, self._policies.get(source, {}))
            self._backends[source] = backend
        return backend

    @permissions(ContextKind.ADMIN)
    async def flush(self, source: str) -> int:
        """Remove every cached value of a source, return how many."""
        backend = self.backend(source)
        return await backend.flush()

    @permissions(ContextKind.ADMIN)
    async def save_policy(self, source: str, entity: str, *, enabled: bool, ttl: int) -> None:
        """Store the policy of an entity of a source and apply it right away."""
        async with get_database().session_context() as session:
            await cache_policies.save_policy(session, source, entity, enabled=enabled, ttl=ttl)
        await self.load()
        logger.info("Cache policy updated: %s:%s enabled=%s ttl=%s", source, entity, enabled, ttl)

    @permissions(ContextKind.ADMIN)
    async def remove_policies(self, source: str) -> int:
        """Remove the policies of a source and its cached values."""
        async with get_database().session_context() as session:
            removed = await cache_policies.delete_policies(session, source)
        await self.load()
        logger.info("Cache source removed: %s (%s policies)", source, removed)
        return removed

    def add_policies(self, policies: Iterable[CachePolicy]) -> None:
        """Add policies to the registry, replacing the ones of the same entity."""
        for policy in policies:
            self._policies.setdefault(policy.source, {})[policy.entity] = policy
            self._backends.pop(policy.source, None)

    def policies(self, source: str) -> dict[CacheEntity, CachePolicy]:
        """The policies of a source."""
        return dict(self._policies.get(source, {}))

    def sources(self) -> list[str]:
        """The sources that have at least one policy."""
        return sorted(self._policies)


@cache
def get_cache_registry() -> CacheRegistry:
    return CacheRegistry()
