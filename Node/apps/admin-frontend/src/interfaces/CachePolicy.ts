export interface ICachePolicy {
    id: number;
    source: string | null;
    entity: string;
    enabled: boolean;
    ttl: number;
}

export interface ICachePolicyPayload {
    source: string | null;
    entity: string;
    enabled: boolean;
    ttl: number;
}

export interface ICachePolicyPatch {
    enabled?: boolean;
    ttl?: number;
}

// Data sources that can back a multi-source cache entity.
export const CACHE_SOURCES: { label: string; value: string }[] = [
    { label: "FESCO", value: "fesco" },
    { label: "Internal", value: "internal" },
];

// Cache entities that can be cached.
export enum CacheEntity {
    DEPARTURES = "departures",
    DESTINATIONS = "destinations",
    CONTAINERS = "containers",
    ROUTES = "routes",
    POINTS = "points",
    RATES = "rates",
    SETTINGS = "settings",
    ROUTES_TODAY = "routes_today",
    CONTAINERS_TODAY = "containers_today",
    DEPARTURES_TODAY = "departures_today",
    DESTINATIONS_TODAY = "destinations_today",
}

// Entities that can be cached under multiple sources (e.g. FESCO departures
// and internal departures). For these entities source is required.
// All other entities are single-source: source is null.
export const MULTI_SOURCE_ENTITIES: { label: string; value: CacheEntity }[] = [
    { label: "Departures", value: CacheEntity.DEPARTURES },
    { label: "Destinations", value: CacheEntity.DESTINATIONS },
    { label: "Containers", value: CacheEntity.CONTAINERS },
    { label: "Routes", value: CacheEntity.ROUTES },
    { label: "Points", value: CacheEntity.POINTS },
    { label: "Departures (today)", value: CacheEntity.DEPARTURES_TODAY },
    { label: "Destinations (today)", value: CacheEntity.DESTINATIONS_TODAY },
    { label: "Containers (today)", value: CacheEntity.CONTAINERS_TODAY },
    { label: "Routes (today)", value: CacheEntity.ROUTES_TODAY },
];

export const SINGLE_SOURCE_ENTITIES: { label: string; value: CacheEntity }[] = [
    { label: "Rates (CBR)", value: CacheEntity.RATES },
    { label: "Settings (internal)", value: CacheEntity.SETTINGS },
];

export function requiresSource(entity: string): boolean {
    return MULTI_SOURCE_ENTITIES.some(e => e.value === entity);
}
