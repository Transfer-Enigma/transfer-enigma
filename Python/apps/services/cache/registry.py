import logging
from functools import cache

from data.cache.cache_policies import is_multi_source
from data.cache.storage import CacheStorage, RedisStorage
from services.cache.backend import CacheBackend
from shared.database import get_database
from shared.models.cache import CacheEntity, CachePolicy
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


@cache
def get_cache_registry() -> CacheRegistry:
    return CacheRegistry()
