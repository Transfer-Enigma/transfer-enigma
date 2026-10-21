import logging
from functools import cache

from shared.cache import CacheBackend, CacheEntity, CachePolicy, CacheStorage, RedisStorage
from shared.database import get_database
from shared.orm.cache_policy import CachePolicyModel
from sqlalchemy import select

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
            result = await session.execute(select(CachePolicyModel))
            models = list(result.scalars().all())

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

    def policies(self, source: str) -> dict[CacheEntity, CachePolicy]:
        """The policies of a source."""
        return dict(self._policies.get(source, {}))

    def sources(self) -> list[str]:
        """The sources that have at least one policy."""
        return sorted(self._policies)


@cache
def get_cache_registry() -> CacheRegistry:
    return CacheRegistry()
