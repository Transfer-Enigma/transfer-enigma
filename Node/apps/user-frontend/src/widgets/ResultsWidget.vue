<script setup lang="ts">
import type {
    IMultiPriceSegment,
    ISinglePriceSegment,
    RouteExtendedDescriptor
} from "@/interfaces/Routes";

import ResultRouteView from "@/components/ResultRouteView.vue";
import RoutesSVG from "@/components/RoutesSVG.vue";

import { revalidateRoutes } from "@/services/calculator";
import { inject, provide, ref, watch } from "vue";

import type { Ref } from "vue";

const props = defineProps<{
    routes: RouteExtendedDescriptor[],
}>();

const editMode: Ref<boolean> = inject("editable") || ref(false);

const buildErrorMessage = (
    val: number,
    routeIndex: number,
    segmentIndex: number,
    priceIndex?: number,
) => (
    `Can not set price ${val} to route `
    + `with route index = ${routeIndex}, segment index = ${segmentIndex}`
    + (priceIndex === undefined ? "" : ` and price index = ${priceIndex}`)
    + ": element is undefined"
);

const allRoutesSelected = (routes: RouteExtendedDescriptor[]) => {
    for (const route of routes)
        if (!route[1][2]) return false;

    return true;
}

const areAllRoutesSelected = ref<boolean>(allRoutesSelected(props.routes));
const areAllRoutesSelectedSignalRef = ref<boolean>(areAllRoutesSelected.value);
provide("allRoutesSelected", areAllRoutesSelected);
provide("allRoutesSelectedSignal", areAllRoutesSelectedSignalRef);
let quietAllRoutesSelectedChange: boolean = false;

function updateSinglePrice(
    val: number,
    segmentIndex: number,
    routeIndex: number,
) {
    const route = props.routes[routeIndex]?.[0][0];
    if (!route)
        throw new Error(buildErrorMessage(val, routeIndex, segmentIndex));

    const segment = (route as ISinglePriceSegment[])[segmentIndex];
    if (!segment)
        throw new Error(buildErrorMessage(val, routeIndex, segmentIndex));

    segment.price = val;
    revalidateRoutes(false);
}

function updateMultiPrice(
    val: number,
    priceIndex: number,
    segmentIndex: number,
    routeIndex: number,
) {
    const route = props.routes[routeIndex]?.[0][0];
    if (!route)
        throw new Error(buildErrorMessage(val, routeIndex, segmentIndex, priceIndex));

    const priceVariant = (route as IMultiPriceSegment[])[segmentIndex]?.prices[priceIndex];
    if (!priceVariant)
        throw new Error(buildErrorMessage(val, routeIndex, segmentIndex, priceIndex));

    priceVariant.value = val;
    revalidateRoutes(false);
}

function setIsRouteSelected(val: boolean, routeIndex: number) {
    const route = props.routes[routeIndex];
    if (!route)
        throw new Error(`Can not ${val ? "" : "un"}select route with index ${routeIndex}: undefined`);

    route[1][2] = val;

    if (!val && areAllRoutesSelected.value) {
        quietAllRoutesSelectedChange = true;
        areAllRoutesSelected.value = false;
    } else if (
        val && !areAllRoutesSelected.value
        && allRoutesSelected(props.routes)
    ) {
        quietAllRoutesSelectedChange = true;
        areAllRoutesSelected.value = true;
    }
}

function updateServiceChecked(val: boolean, serviceIndex: number, routeIndex: number) {
    const service = props.routes[routeIndex]?.[0][3][serviceIndex];
    if (!service)
        throw new Error(`Service [${serviceIndex}] not found in route [${routeIndex}]`);

    service.checked = val;
    revalidateRoutes(false);
}

watch(areAllRoutesSelected, () => {
    if (quietAllRoutesSelectedChange) quietAllRoutesSelectedChange = false;
    else areAllRoutesSelectedSignalRef.value = !areAllRoutesSelectedSignalRef.value;
});
</script>

<template>
    <div v-show="editMode" class="mb-4">
        <label for="select-all-routes">Добавить все маршруты в КП: </label>
        <input id="select-all-routes" class="m-2" type="checkbox" v-model="areAllRoutesSelected">
    </div>

    <div hidden="hidden">
        <RoutesSVG />
    </div>

    <div id="results-direct" class="mt-4" v-if="props.routes.length">
        <ResultRouteView
            v-for="(route, index) in props.routes"
            :key="index"
            :route="route"
            @update:single-price="(val: number, segId: number) => updateSinglePrice(val, segId, index)"
            @update:multi-price="(val: number, segId: number, routeId: number) => updateMultiPrice(val, segId, routeId, index)"
            @set-selected="(val: boolean) => setIsRouteSelected(val, index)"
            @update:serviceChecked="(val: boolean, serviceIndex: number) => updateServiceChecked(val, serviceIndex, index)"
        />
    </div>
    <div v-else>
        <h5>Не найдены</h5>
    </div>
</template>

<style scoped></style>
