import { fetchAsJSON } from "@/helpers/requests";
import { serializeIds } from "@/services/points";

import type { IDataWithErrors } from "@/interfaces/APIResponses";
import type { IdIsExternal, IPoint } from "@/interfaces/Point";

export async function getDepartures(date: string): Promise<IDataWithErrors<IPoint[]>> {
    return (await fetchAsJSON(`/api/v2/points/departures?date=${date}`)) as IDataWithErrors<IPoint[]>;
}

export async function getDestinations(
    date: string,
    departureIds: IdIsExternal[],
): Promise<IDataWithErrors<IPoint[]>> {
    return (await fetchAsJSON(
        `/api/v2/points/destinations?date=${date}&departure_point_ids=${serializeIds(departureIds)}`
    )) as IDataWithErrors<IPoint[]>;
}

export async function getTruckDepartures(date: string): Promise<IDataWithErrors<IPoint[]>> {
    return (await fetchAsJSON(`/api/v2/points/truck-departures?date=${date}`)) as IDataWithErrors<IPoint[]>;
}

export async function getTruckDestinations(date: string): Promise<IDataWithErrors<IPoint[]>> {
    return (await fetchAsJSON(`/api/v2/points/truck-destinations?date=${date}`)) as IDataWithErrors<IPoint[]>;
}
