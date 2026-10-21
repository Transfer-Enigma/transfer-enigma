from dataclasses import dataclass

from .entity import CacheEntity


@dataclass(frozen=True)
class CachePolicy:
    """Caching configuration of one entity of one source.

    It mirrors one row of the cache_policies table: an entity is only
    cached when a policy for it exists and is enabled.
    """

    source: str
    entity: CacheEntity
    enabled: bool
    ttl: int
