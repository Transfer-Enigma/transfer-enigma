<script setup lang="ts">
import type {
    IMultiPriceSegment,
    ISinglePriceSegment,
    RouteDescriptor,
    RouteExtendedDescriptor
} from "@/interfaces/Routes";

import ResultRouteView from "@/components/ResultRouteView.vue";
import RoutesSVG from "@/components/RoutesSVG.vue";

import { useToast } from "@/composables/useToast";
import { createCollection } from "@/api_helpers/collections";
import { revalidateRoutes } from "@/services/calculator";
import { getRouteLinkIds } from "@/services/routeLinks";
import { useDemoAuth } from "@/stores/demoAuth";
import { computed, inject, provide, ref, watch } from "vue";

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

const pickedDescriptors = ref<RouteDescriptor[]>([]);
const pickedCount = computed((): number => pickedDescriptors.value.length);
const creatingCollection = ref<boolean>(false);
const collectionPath = ref<string | null>(null);
const collectionUrl = computed((): string | null =>
    collectionPath.value ? `${window.location.origin}${collectionPath.value}` : null);

function isPicked(route: RouteDescriptor): boolean {
    return pickedDescriptors.value.includes(route);
}

function togglePicked(val: boolean, routeIndex: number) {
    const descriptor = props.routes[routeIndex]?.[0];
    if (!descriptor)
        throw new Error(`Can not pick route with index ${routeIndex}: undefined`);

    if (val) {
        if (!pickedDescriptors.value.includes(descriptor))
            pickedDescriptors.value.push(descriptor);
    } else {
        pickedDescriptors.value = pickedDescriptors.value.filter((item) => item !== descriptor);
    }
}

async function createCollectionFromPicked() {
    creatingCollection.value = true;
    collectionPath.value = null;

    try {
        const present = new Set(props.routes.map((route) => route[0]));
        const items = [];
        for (const descriptor of pickedDescriptors.value) {
            if (!present.has(descriptor))
                continue;

            const ids = getRouteLinkIds(descriptor);
            if (!ids)
                continue;

            items.push({ segments: ids.segmentIds, services: ids.serviceIds });
        }

        if (!items.length) {
            useToast().show("Нет маршрутов для подборки", "warning");
            return;
        }

        const uid = await createCollection(items);
        const demoUid = useDemoAuth().demoUid;
        collectionPath.value = demoUid
            ? `/demo/${encodeURIComponent(demoUid)}/collections/${uid}`
            : `/collections/${uid}`;
        pickedDescriptors.value = [];
    } catch (e) {
        console.log(e);
        useToast().show("Не удалось создать подборку", "error");
    } finally {
        creatingCollection.value = false;
    }
}

async function copyCollectionLink() {
    if (!collectionUrl.value)
        return;

    try {
        await navigator.clipboard.writeText(collectionUrl.value);
        useToast().show("Ссылка на подборку скопирована", "success");
    } catch (e) {
        console.log(e);
        useToast().show(collectionUrl.value, "warning", 10000);
    }
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

    <div v-if="pickedCount > 0" class="mb-3">
        <button class="btn btn-primary" :disabled="creatingCollection" @click="createCollectionFromPicked">
            Создать подборку из выбранных ({{ pickedCount }})
        </button>
    </div>

    <div v-if="collectionUrl" class="alert alert-success">
        Ссылка на подборку:
        <a :href="collectionPath">{{ collectionUrl }}</a>
        <button class="btn btn-outline-primary btn-sm ms-2" @click="copyCollectionLink">Скопировать</button>
    </div>

    <div id="results-direct" class="mt-4" v-if="props.routes.length">
        <ResultRouteView
            v-for="(route, index) in props.routes"
            :key="index"
            :route="route"
            :picked="isPicked(route[0])"
            @update:single-price="(val: number, segId: number) => updateSinglePrice(val, segId, index)"
            @update:multi-price="(val: number, segId: number, routeId: number) => updateMultiPrice(val, segId, routeId, index)"
            @set-selected="(val: boolean) => setIsRouteSelected(val, index)"
            @update:serviceChecked="(val: boolean, serviceIndex: number) => updateServiceChecked(val, serviceIndex, index)"
            @update:picked="(val: boolean) => togglePicked(val, index)"
        />
    </div>
    <div v-else>
        <h5>Не найдены</h5>
    </div>
</template>

<style scoped></style>
