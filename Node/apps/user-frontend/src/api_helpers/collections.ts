import type { IDrop, Route, RouteDescriptor } from "@/interfaces/Routes";
import type { IService } from "@/interfaces/Service";
import { fetchAsJSON } from "@/helpers/requests";

export interface CollectionItemPayload {
    segments: number[];
    services: number[];
}

interface CollectionRoutePayload {
    segments: Route;
    drop: IDrop | null;
    may_be_invalid: boolean;
    services: IService[];
}

interface CollectionResponse {
    uid: string;
    routes: CollectionRoutePayload[];
}

function toRouteDescriptors(response: CollectionResponse): RouteDescriptor[] {
    return response.routes.map((item) => [
        item.segments,
        item.drop as IDrop,
        item.may_be_invalid,
        item.services ?? [],
    ]);
}

export async function createCollection(items: CollectionItemPayload[]): Promise<string> {
    const response = await fetchAsJSON("/api/v2/collections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items }),
    }) as { uid: string };
    return response.uid;
}

export async function getCollection(uid: string): Promise<RouteDescriptor[]> {
    const url = `/api/v2/collections/${encodeURIComponent(uid)}`;
    const res = await fetch(url, { method: "GET" });
    if (!res.ok)
        throw new Error(`Got an error while executing GET ${url} [${res.status}]\n${await res.text()}`);

    return toRouteDescriptors(await res.json() as CollectionResponse);
}

export async function getDemoCollection(uid: string): Promise<RouteDescriptor[]> {
    const url = `/api/v2/collections/${encodeURIComponent(uid)}`;
    const response = await fetchAsJSON(url, { method: "GET" });
    return toRouteDescriptors(response as CollectionResponse);
}
