<script setup lang="ts">
import CalculationStatusIndicator from "@/components/CalculationStatusIndicator.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import CalculatorForm from "@/widgets/CalculatorForm.vue";
import CurrencySelect from "@/widgets/CurrencySelect.vue";
import ResultsWidget from "@/widgets/ResultsWidget.vue";

import { clearRoutes, revalidateRoutes, serializeCalculatorQueryParams, updateRoutesSSE } from "@/services/calculator";
import { useCalculationStatus } from "@/composables/useCalculationStatus";
import { useDemoAuth } from "@/stores/demoAuth";
import { useRates } from "@/stores/rates";
import { useRoutes } from "@/stores/routes";

import { useRouter } from "vue-router";
import { computed, nextTick, onMounted, provide, ref } from "vue";

import type { IdIsExternal } from "@/interfaces/Point";
import type { RatesMap } from "@/stores/rates";
import type { RouteExtendedDescriptor } from "@/interfaces/Routes";
import type { Ref } from "vue";

interface Props {
    date?: string;
    departureIds?: IdIsExternal[];
    destinationIds?: IdIsExternal[];
    containerType?: string;
    containerWeight?: number;
    currency?: string;
    headTruck?: boolean;
    tailTruck?: boolean;
}

const props = defineProps<Props>();

const ratesStore = useRates();
const ratesRef = computed((): RatesMap => ratesStore.rates);
const currentRateRef = computed({
    get() { return ratesStore.currentRate; },
    set(val: string) {
        const locker = ratesStore.getLocker();
        if (locker) locker.then(() => {
            ratesStore.setCurrentRate(val);
            revalidateRoutes();
        });
        else ratesStore.setCurrentRate(val);
    },
});

const routesStore = useRoutes();
const routesRef = computed((): RouteExtendedDescriptor[] | undefined => routesStore.routes);

const isDemoModeActive = computed(() => useDemoAuth().isDemo);  // TODO: use feature-flags
provide("isDemoModeActive", isDemoModeActive);

const editMode = ref<boolean>(false);

provide("editable", editMode);
const router = useRouter();

const resultsElementRef = ref<HTMLElement | undefined>();

const dateModel = ref<string | undefined>();
if (!dateModel.value) dateModel.value = new Date().toLocaleDateString("en-CA");

const departureIdsModel = ref<IdIsExternal[]>();
const destinationIdsModel = ref<IdIsExternal[]>();
const containerTypeModel = ref<string>("20");
const containerWeightModel = ref<number>();
const headTruckModel = ref<boolean>(false);
const tailTruckModel = ref<boolean>(false);

const loading = ref(false);

const models: { [key: string]: Ref<unknown> } = {
    date: dateModel,
    departureIds: departureIdsModel,
    destinationIds: destinationIdsModel,
    containerType: containerTypeModel,
    containerWeight: containerWeightModel,
};

for (const [key, val] of Object.entries(props)) {
    if (val === undefined) continue;

    if (models[key]) models[key].value = val;
}

if (props.headTruck !== undefined) headTruckModel.value = props.headTruck;
if (props.tailTruck !== undefined) tailTruckModel.value = props.tailTruck;

async function calculate(pushURL: boolean = true) {
    loading.value = true;

    await nextTick();
    resultsElementRef.value?.scrollIntoView({ behavior: "smooth" });

    await ratesStore.getLocker();

    if (pushURL)
        await router.push({
            query: serializeCalculatorQueryParams({
                date: dateModel.value,
                departureIds: departureIdsModel.value,
                destinationIds: destinationIdsModel.value,
                containerType: containerTypeModel.value,
                containerWeight: containerWeightModel.value,
                currency: ratesStore.currentRate,
                headTruck: headTruckModel.value,
                tailTruck: tailTruckModel.value,
            }),
        });

    await updateRoutesSSE({
        date: dateModel.value,
        departureIds: departureIdsModel.value,
        destinationIds: destinationIdsModel.value,
        containerType: containerTypeModel.value,
        containerWeight: containerWeightModel.value,
        headTruck: headTruckModel.value,
        tailTruck: tailTruckModel.value,
    });

    loading.value = false;
}

function reset() {
    router.push({ query: {} });
    dateModel.value = new Date().toLocaleDateString("en-CA");
    currentRateRef.value = "RUB";
    loading.value = false;
    departureIdsModel.value = undefined;
    destinationIdsModel.value = undefined;
    headTruckModel.value = false;
    tailTruckModel.value = false;
    clearRoutes();
    useCalculationStatus().reset();
}

async function saveInPdf() {
    editMode.value = false;
    await nextTick();

    document.getElementById("app")?.setAttribute("data-print-routes", "");
    window.print();
    document.getElementById("app")?.removeAttribute("data-print-routes");
}

onMounted(() => {
    currentRateRef.value = props.currency ?? "RUB";

    const data = [
        props.date,
        props.departureIds,
        props.destinationIds,
        props.containerType,
        props.containerWeight,
        props.currency,
    ];
    let allParamsSent = true;
    for (const item of data)
        if (item === undefined) {
            allParamsSent = false;
            break;
        }

    if (allParamsSent) nextTick().then(() => calculate(false));
});
</script>

<template>
    <div class="my-5 print-mode--hidden">
        <div class="card shadow-sm rounded-4 p-4">
            <h2 class="mb-4 text-center">Калькулятор маршрутов</h2>

            <CalculatorForm
                v-model:date="dateModel"
                v-model:departure="departureIdsModel"
                v-model:destination="destinationIdsModel"
                v-model:container-type="containerTypeModel"
                v-model:container-weight="containerWeightModel"
                v-model:head-truck="headTruckModel"
                v-model:tail-truck="tailTruckModel"
                @calculate="calculate"
                @reset="reset"
            />
        </div>

        <hr />
        <h3>Просуммировать стоимость маршрутов в валюте:</h3>
        <div class="mb-3 position-relative">
            <CurrencySelect :rates="ratesRef" v-model="currentRateRef" />
        </div>

        <template v-if="!isDemoModeActive">
            <button class="btn btn-secondary" @click="editMode = !editMode">
                <template v-if="editMode">
                    Обычный режим
                </template>
                <template v-else>
                    Режим редактирования КП
                </template>
            </button>

            <button class="btn btn-success" :disabled="!routesRef" @click="saveInPdf">Сохранить результат в PDF</button>
        </template>
    </div>

    <hr />

    <div ref="resultsElementRef" class="results" v-if="loading || routesRef">
        <div class="text-center" v-if="loading"><LoadingSpinner /></div>
        <ResultsWidget v-if="routesRef" :routes="routesRef!" />
    </div>

    <CalculationStatusIndicator />
</template>

<style scoped>
.results {
    min-height: 80vh;
}
</style>
