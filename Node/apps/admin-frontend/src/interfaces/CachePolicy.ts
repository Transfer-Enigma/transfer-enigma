export interface ICachePolicy {
    id: number;
    source: string;
    entity: string;
    enabled: boolean;
    ttl: number;
}

export interface ICachePolicyPayload {
    source: string;
    entity: string;
    enabled: boolean;
    ttl: number;
}

export interface ICachePolicyPatch {
    entity?: string;
    enabled?: boolean;
    ttl?: number;
}

export const CACHE_ENTITIES: { label: string; value: string }[] = [
    { label: "Departures", value: "departures" },
    { label: "Destinations", value: "destinations" },
    { label: "Containers", value: "containers" },
    { label: "Routes", value: "routes" },
    { label: "Points", value: "points" },
    { label: "Rates", value: "rates" },
    { label: "Settings", value: "settings" },
];
