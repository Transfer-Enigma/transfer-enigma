import type { RouteDescriptor } from "@/interfaces/Routes";

export interface RouteLinkIds {
    segmentIds: number[];
    serviceIds: number[];
}

export function getRouteLinkIds(route: RouteDescriptor): RouteLinkIds | null {
    const segments = route[0];
    if (!segments.length || !segments.every((segment) => typeof segment.id === "number"))
        return null;

    const serviceIds = (route[3] ?? [])
        .filter((service) => service.checked && typeof service.id === "number" && service.id !== null)
        .map((service) => service.id as number);

    return {
        segmentIds: segments.map((segment) => segment.id as number),
        serviceIds,
    };
}

export function buildRouteLink(route: RouteDescriptor, demoUid: string | null): string | null {
    const ids = getRouteLinkIds(route);
    if (!ids)
        return null;

    const params = new URLSearchParams({ segments: ids.segmentIds.join(",") });
    if (ids.serviceIds.length)
        params.set("included-services", ids.serviceIds.join(","));

    const base = demoUid ? `/demo/${encodeURIComponent(demoUid)}/route` : "/route";
    return `${base}?${params.toString()}`;
}
