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

// Entities that can be cached under multiple sources (e.g. FESCO departures
// and internal departures). For these entities source is required.
// All other entities are single-source: source is null.
export const MULTI_SOURCE_ENTITIES: { label: string; value: string }[] = [
    { label: "Departures", value: "departures" },
    { label: "Destinations", value: "destinations" },
    { label: "Containers", value: "containers" },
    { label: "Routes", value: "routes" },
    { label: "Points", value: "points" },
    { label: "Departures (today)", value: "departures_today" },
    { label: "Destinations (today)", value: "destinations_today" },
    { label: "Containers (today)", value: "containers_today" },
    { label: "Routes (today)", value: "routes_today" },
];

export const SINGLE_SOURCE_ENTITIES: { label: string; value: string }[] = [
    { label: "Rates (CBR)", value: "rates" },
    { label: "Settings (internal)", value: "settings" },
];

export function requiresSource(entity: string): boolean {
    return MULTI_SOURCE_ENTITIES.some(e => e.value === entity);
}
