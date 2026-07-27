import { deserializeIds, serializeIds } from "./points";
import { getRoutesSSE } from "@/api_helpers/routes";
import { RouteType } from "@/interfaces/Routes";
import { convertToCurrentRate } from "@/services/rates";
import { useRates } from "@/stores/rates";
import { useRoutes } from "@/stores/routes";
import { roundPrice } from "@/helpers/roundPrice";
import { useCalculationStatus } from "@/composables/useCalculationStatus";
import { useToast } from "@/composables/useToast";

import type { ICalculatorPayload, ICalculatorPayloadWithCurrency } from "@/interfaces/CalculatorPayload";
import type {
    IMultiPriceSegment,
    ISinglePriceSegment,
    PriceDescriptor,
    PriceRange,
    RouteDescriptor,
    RouteExtendedDescriptor,
} from "@/interfaces/Routes";

export const serializeCalculatorQueryParams = (payload: ICalculatorPayloadWithCurrency) => ({
    date: payload.date,
    departureIds: payload.departureIds ? serializeIds(payload.departureIds) : undefined,
    destinationIds: payload.departureIds && payload.destinationIds ? serializeIds(payload.destinationIds) : undefined,
    type: payload.containerType,
    weight: payload.containerWeight,
    currency: payload.currency,
    headTruck: payload.headTruck ? "1" : undefined,
    tailTruck: payload.tailTruck ? "1" : undefined,
});

export function deserializeCalculatorQueryParams(query: Record<string, unknown>) {
    const params: Record<string, unknown> = {};

    if (query.currency) params.currency = query.currency;

    if (query.date && !Number.isNaN(new Date(query.date as string).getDate()))
        params.date = query.date;

    if (query.departureIds) {
        params.departureIds = deserializeIds(query.departureIds as string);

        if (query.destinationIds)
            params.destinationIds = deserializeIds(query.destinationIds as string);
    }

    if (query.type) params.containerType = query.type;

    if (query.weight) params.containerWeight = Number(query.weight);

    if (query.headTruck) params.headTruck = true;

    if (query.tailTruck) params.tailTruck = true;

    return params;
}

export async function updateRoutesSSE(payload: ICalculatorPayload) {
    if (
        !payload.date
        || !payload.departureIds?.length
        || !payload.destinationIds?.length
        || !payload.containerType
        || !payload.containerWeight
    ) throw new Error(`Insufficient payload! ${JSON.stringify(payload)}`);

    const { currentRate } = useRates();
    if (!currentRate)
        throw new Error("No current rate!");

    const departureInternalIds: number[] = [];
    const destinationInternalIds: number[] = [];
    const departureExternalIds: string[] = [];
    const destinationExternalIds: string[] = [];

    for (const departureIdDescriptor of payload.departureIds) {
        if (departureIdDescriptor.isExternal)
            departureExternalIds.push(departureIdDescriptor.id as string);
        else
            departureInternalIds.push(departureIdDescriptor.id as number);
    }

    for (const destinationIdDescriptor of payload.destinationIds) {
        if (destinationIdDescriptor.isExternal)
            destinationExternalIds.push(destinationIdDescriptor.id as string);
        else
            destinationInternalIds.push(destinationIdDescriptor.id as number);
    }

    const routesStore = useRoutes();
    const collected: RouteDescriptor[] = [];
    const calcStatus = useCalculationStatus();
    let hasWarnings = false;

    routesStore.setRoutes();
    calcStatus.setStatus("loading");

    try {
        for await (const event of getRoutesSSE({
            dispatchDate: payload.date,
            departureInternalIds,
            destinationInternalIds,
            departureExternalIds,
            destinationExternalIds,
            containerType: payload.containerType,
            cargoWeight: payload.containerWeight,
            currency: currentRate,
            headTruck: payload.headTruck,
            tailTruck: payload.tailTruck,
        })) {
            if (event.type === "route") {
                collected.push(event.route);
                routesStore.setRoutes(processRoutes(collected, true));
            } else if (event.type === "error") {
                hasWarnings = true;
                calcStatus.setStatus("loading-warnings");
                useToast().show(
                    `Ошибка: ${event.error.error_text}`,
                    "warning",
                );
            }
        }
    } catch (e) {
        calcStatus.setStatus("error");
        if (e instanceof DOMException && e.name === "AbortError") {
            useToast().show("Превышено время ожидания ответа от сервера", "error");
        } else {
            useToast().show(
                e instanceof Error ? e.message : "Неизвестная ошибка",
                "error",
            );
        }
        return;
    }

    routesStore.setRoutes(processRoutes(collected, true));

    if (collected.length > 0) {
        calcStatus.setStatus(hasWarnings ? "warnings" : "completed");
        useToast().show(
            hasWarnings
                ? "Расчёт маршрутов завершён с предупреждениями"
                : "Расчёт маршрутов завершён",
            "success",
        );
    } else {
        calcStatus.setStatus("completed");
        useToast().show("Маршруты не найдены", "warning");
    }
}

export function revalidateRoutes(resort: boolean = true) {
    const routes = useRoutes().routes;
    if (!routes)
        return;

    useRoutes().setRoutes(processRoutes(routes, resort));
}

export const clearRoutes = () => useRoutes().setRoutes();

function processRoutes(routes: (RouteDescriptor | RouteExtendedDescriptor)[], sort: boolean): RouteExtendedDescriptor[] {
    const result: RouteExtendedDescriptor[] = Array.from({ length: routes.length });

    for (const key in routes) {
        const route = routes[key];
        if (!route)
            continue;

        let minSumPrice: number = 0, minSumPriceWithConv: number = 0;
        let maxSumPrice: number = 0, maxSumPriceWithConv: number = 0;

        const routeDescriptor = route.length === 2 ? (route as RouteExtendedDescriptor)[0] : (route as RouteDescriptor);

        for (const segment of routeDescriptor[0]) {
            if ((segment as ISinglePriceSegment).price) {
                const singlePriceSegment = segment as ISinglePriceSegment;

                // Without conversation percents
                const [inc] = convertToCurrentRate(singlePriceSegment.price, singlePriceSegment.currency);

                minSumPrice += inc;
                maxSumPrice += inc;
                // Without conversation percents
                minSumPriceWithConv += inc;
                maxSumPriceWithConv += inc;
            } else {
                const multiPriceSegment = segment as IMultiPriceSegment;
                if (multiPriceSegment.type === RouteType.SEA_RAIL) {
                    for (const price of multiPriceSegment.prices) {
                        const [inc, incWithConv] = convertToCurrentRate(price.value, price.currency, price.conversation_percents);

                        minSumPrice += inc;
                        maxSumPrice += inc;

                        minSumPriceWithConv += incWithConv;
                        maxSumPriceWithConv += incWithConv;
                    }
                } else {
                    let minLocalPrice: number | undefined = undefined,
                        minLocalPriceWithConv: number | undefined = undefined;
                    let maxLocalPrice: number | undefined = undefined,
                        maxLocalPriceWithConv: number | undefined = undefined;

                    for (const price of multiPriceSegment.prices) {
                        const [val, valWithConv] = convertToCurrentRate(price.value, price.currency, price.conversation_percents);

                        if (minLocalPrice === undefined || minLocalPrice > val)
                            minLocalPrice = val;
                        if (maxLocalPrice === undefined || maxLocalPrice < val)
                            maxLocalPrice = val;

                        if (minLocalPriceWithConv === undefined || minLocalPriceWithConv > valWithConv)
                            minLocalPriceWithConv = valWithConv;
                        if (maxLocalPriceWithConv === undefined || maxLocalPriceWithConv < valWithConv)
                            maxLocalPriceWithConv = valWithConv;
                    }

                    minSumPrice += minLocalPrice ?? 0;
                    maxSumPrice += maxLocalPrice ?? 0;

                    minSumPriceWithConv += minLocalPriceWithConv ?? 0;
                    maxSumPriceWithConv += maxLocalPriceWithConv ?? 0;
                }
            }
        }

        const drop = routeDescriptor[1];
        if (drop?.price) {
            const [inc, incWithConv] = convertToCurrentRate(drop.price, drop.currency, drop.conversation_percents);

            minSumPrice += inc;
            maxSumPrice += inc;

            minSumPriceWithConv += incWithConv;
            maxSumPriceWithConv += incWithConv;
        }

        const services = routeDescriptor[3];
        for (const service of services) {
            if (!service.checked)
                continue;

            const [inc, incWithConv] = convertToCurrentRate(service.price, service.currency);

            minSumPrice += inc;
            maxSumPrice += inc;

            minSumPriceWithConv += incWithConv;
            maxSumPriceWithConv += incWithConv;
        }

        minSumPrice = roundPrice(minSumPrice);
        maxSumPrice = roundPrice(maxSumPrice);
        minSumPriceWithConv = roundPrice(minSumPriceWithConv);
        maxSumPriceWithConv = roundPrice(maxSumPriceWithConv);

        result[key] = [
            routeDescriptor,
            [
                (maxSumPrice - minSumPrice > Number.EPSILON
                    ? [minSumPrice, maxSumPrice]
                    : minSumPrice) as PriceDescriptor,
                (maxSumPriceWithConv - minSumPriceWithConv > Number.EPSILON
                    ? [minSumPriceWithConv, maxSumPriceWithConv]
                    : minSumPriceWithConv) as PriceDescriptor,
                route.length === 2 ? (route as RouteExtendedDescriptor)[1][2] : false,
            ],
        ];
    }

    if (sort)
        result.sort((a: RouteExtendedDescriptor, b: RouteExtendedDescriptor) =>
            (Number.isNaN(a[1][1]) ? (a[1][1] as PriceRange)[0] : a[1][1] as number)
            - (Number.isNaN(b[1][1]) ? (b[1][1] as PriceRange)[0] : b[1][1] as number));

    return result;
}
