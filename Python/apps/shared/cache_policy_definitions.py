from dataclasses import dataclass


@dataclass(frozen=True)
class CachePolicyDefinition:
    source: str | None
    entity: str
    enabled: bool
    ttl: int
    description: str = ""


CACHE_POLICY_DEFINITIONS: list[CachePolicyDefinition] = [
    CachePolicyDefinition(
        source=None,
        entity="rates",
        enabled=True,
        ttl=3600,
        description="Currency rates from the CBR API",
    ),
    CachePolicyDefinition(
        source="fesco",
        entity="departures",
        enabled=True,
        ttl=86400,
        description="FESCO departure points for past and future dates",
    ),
    CachePolicyDefinition(
        source="fesco",
        entity="destinations",
        enabled=True,
        ttl=86400,
        description="FESCO destination points for past and future dates",
    ),
    CachePolicyDefinition(
        source="fesco",
        entity="containers",
        enabled=True,
        ttl=86400,
        description="FESCO containers for past and future dates",
    ),
    CachePolicyDefinition(
        source="fesco",
        entity="routes",
        enabled=True,
        ttl=86400,
        description="FESCO routes for past and future dates",
    ),
    CachePolicyDefinition(
        source="fesco",
        entity="departures_today",
        enabled=True,
        ttl=600,
        description="FESCO departure points for today",
    ),
    CachePolicyDefinition(
        source="fesco",
        entity="destinations_today",
        enabled=True,
        ttl=600,
        description="FESCO destination points for today",
    ),
    CachePolicyDefinition(
        source="fesco",
        entity="containers_today",
        enabled=True,
        ttl=600,
        description="FESCO containers for today",
    ),
    CachePolicyDefinition(
        source="fesco",
        entity="routes_today",
        enabled=True,
        ttl=600,
        description="FESCO routes for today",
    ),
    CachePolicyDefinition(
        source="fesco",
        entity="points",
        enabled=True,
        ttl=86400,
        description="FESCO points for past and future dates",
    ),
    CachePolicyDefinition(
        source="internal",
        entity="points",
        enabled=False,
        ttl=86400,
        description="Internal points for past and future dates",
    ),
    CachePolicyDefinition(
        source="fesco",
        entity="points_today",
        enabled=True,
        ttl=600,
        description="FESCO points for today",
    ),
    CachePolicyDefinition(
        source="internal",
        entity="points_today",
        enabled=False,
        ttl=600,
        description="Internal points for today",
    ),
]


def get_cache_policy_definitions() -> list[CachePolicyDefinition]:
    return CACHE_POLICY_DEFINITIONS


def get_cache_policy_definition(source: str | None, entity: str) -> CachePolicyDefinition | None:
    for defn in CACHE_POLICY_DEFINITIONS:
        if defn.source == source and defn.entity == entity:
            return defn
    return None
