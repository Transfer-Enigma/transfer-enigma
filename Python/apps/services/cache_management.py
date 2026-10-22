import logging

from data.cache.registry import get_cache_registry
from shared.cache import CacheEntity

logger = logging.getLogger(__name__)


async def list_sources() -> list[dict]:
    """The sources that have a policy, with the policy of every entity."""
    registry = get_cache_registry()

    sources: dict[str, list[dict]] = {}
    for source in registry.sources():
        entities = [
            {"entity": entity.value, "enabled": policy.enabled, "ttl": policy.ttl}
            for entity, policy in sorted(registry.policies(source).items(), key=lambda item: item[0].value)
        ]
        sources[source] = entities

    return [{"source": source, "entities": entities} for source, entities in sorted(sources.items())]


async def list_keys(source: str, entity: str | None = None, limit: int = 100) -> list[str]:
    """The cached keys of a source, or of one of its entities."""
    backend = get_cache_registry().backend(source)
    if entity is None:
        return await backend.keys(limit=limit)
    return await backend.keys(CacheEntity(entity), limit=limit)


async def flush_source(source: str) -> int:
    """Remove every cached value of a source, return how many."""
    return await get_cache_registry().flush(source)


async def update_policy(source: str, entity: str, *, enabled: bool, ttl: int) -> None:
    """Store the policy of an entity of a source and apply it right away."""
    await get_cache_registry().save_policy(source, entity, enabled=enabled, ttl=ttl)


async def remove_source(source: str) -> int:
    """Remove the policies of a source and its cached values."""
    registry = get_cache_registry()
    removed = await registry.remove_policies(source)
    flushed = await registry.flush(source)
    return removed + flushed
