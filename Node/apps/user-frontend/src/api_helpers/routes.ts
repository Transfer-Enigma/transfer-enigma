import type { IError } from "@/interfaces/APIResponses";
import type { ICalculatorReadyToSendPayload } from "@/interfaces/CalculatorPayload";
import type { RouteDescriptor, Route, IDrop } from "@/interfaces/Routes";
import type { IService } from "@/interfaces/Service";
import { fetchAsJSON, fetchSSE } from "@/helpers/requests";

interface RouteResultSSE {
    segments: Route;
    drop: IDrop;
    may_be_invalid: boolean;
    services: IService[];
}

interface RouteDetailResponse {
    segments: Route;
    drop: IDrop | null;
    may_be_invalid: boolean;
    services: IService[];
}

function buildRouteDetailURL(segments: string, includedServices?: string): string {
    const params = new URLSearchParams({ segments });
    if (includedServices)
        params.set("included-services", includedServices);

    return `/api/v2/routes/detail?${params.toString()}`;
}

function toRouteDescriptor(result: RouteDetailResponse): RouteDescriptor {
    return [
        result.segments,
        result.drop as IDrop,
        result.may_be_invalid,
        result.services ?? [],
    ];
}

export async function getRouteDetail(segments: string, includedServices?: string): Promise<RouteDescriptor> {
    const result = await fetchAsJSON(buildRouteDetailURL(segments, includedServices), { method: "GET" });
    return toRouteDescriptor(result as RouteDetailResponse);
}

export async function getRouteDetailWithoutMarkup(
    segments: string,
    includedServices?: string,
): Promise<RouteDescriptor> {
    const url = buildRouteDetailURL(segments, includedServices);
    const res = await fetch(url, { method: "GET" });
    if (!res.ok)
        throw new Error(`Got an error while executing GET ${url} [${res.status}]\n${await res.text()}`);

    return toRouteDescriptor(await res.json() as RouteDetailResponse);
}

export async function* getRoutesSSE(
    payload: ICalculatorReadyToSendPayload,
): AsyncGenerator<{ type: "route"; route: RouteDescriptor } | { type: "error"; error: IError }> {
    const stream = fetchSSE("/api/v3/routes/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    }, 40000);

    for await (const { event, data } of stream) {
        if (event === "route") {
            const result: RouteResultSSE = JSON.parse(data);
            const route: RouteDescriptor = [
                result.segments,
                result.drop,
                result.may_be_invalid,
                result.services,
            ];
            yield { type: "route", route };
        } else if (event === "error") {
            const error: IError = JSON.parse(data);
            yield { type: "error", error };
        } else if (event === "complete") {
            break;
        }
    }
}
