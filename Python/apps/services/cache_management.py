import logging

from data.cache.registry import get_cache_registry
from data.repositories.cache_policies import list_policies
from shared.cache import CacheEntity
from shared.database import get_database

logger = logging.getLogger(__name__)


async def list_sources() -> list[dict]:
    """The sources that have a policy, with the policy of every entity."""
    async with get_database().session_context() as session:
        models = await list_policies(session)

    sources: dict[str, list[dict]] = {}
    for model in models:
        sources.setdefault(model.source, []).append({
            "entity": model.entity,
            "enabled": model.enabled,
            "ttl": model.ttl,
        })

    return [
        {"source": source, "entities": sorted(entities, key=lambda item: item["entity"])}
        for source, entities in sorted(sources.items())
    ]


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
