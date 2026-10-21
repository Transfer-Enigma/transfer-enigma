from dataclasses import dataclass

from .entity import CacheEntity


@dataclass(frozen=True)
class CachePolicy:
    """Caching configuration of one entity of one source.

    It mirrors one row of the cache_policies table: an entity is only
    cached when a policy for it exists and is enabled.

    For multi-source entities (see entity.MULTI_SOURCE_ENTITIES) source is
    required and identifies which provider the data comes from. For
    single-source entities (e.g. rates from CBR, settings from the internal
    DB) source is None — the entity itself identifies the source.
    """

    source: str | None
    entity: CacheEntity
    enabled: bool
    ttl: int
