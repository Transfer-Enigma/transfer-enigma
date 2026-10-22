from enum import StrEnum


class CacheEntity(StrEnum):
    """Entities that can be cached.

    A cache policy may only reference an entity listed here, so a policy
    row with an unknown entity is ignored instead of silently doing
    nothing.
    """

    DEPARTURES = "departures"
    DESTINATIONS = "destinations"
    CONTAINERS = "containers"
    ROUTES = "routes"
    RATES = "rates"
    SETTINGS = "settings"
