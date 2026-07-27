<script setup lang="ts">
import type { IPoint, IdIsExternal } from "@/interfaces/Point";
import PointsSelect from "@/widgets/PointsSelect.vue";

import { getDepartures, getDestinations, getTruckDepartures, getTruckDestinations } from "@/api_helpers/points";
import { useToast } from "@/composables/useToast";
import { computed, onMounted, ref, useId, watch } from "vue";

const dateModel = defineModel<string>("date");
const departureIdsModel = defineModel<IdIsExternal[]>("departure");
const destinationIdsModel = defineModel<IdIsExternal[]>("destination");
const containerTypeModel = defineModel<string>("containerType");
const containerWeightModel = defineModel<number>("containerWeight");

const headTruckModel = defineModel<boolean>("headTruck", { required: false, default: false });
const tailTruckModel = defineModel<boolean>("tailTruck", { required: false, default: false });

const emit = defineEmits(["calculate", "reset"]);

const dateInputId = useId();
const containerTypeSelectId = useId();
const containerWeightInputId = useId();

const departureInputText = ref<string>("");
const destinationInputText = ref<string>("");
const departurePoints = ref<IPoint[]>([]);
const destinationPoints = ref<IPoint[]>([]);
const truckDeparturePoints = ref<IPoint[]>([]);
const truckDestinationPoints = ref<IPoint[]>([]);
const calcForm = ref<HTMLFormElement>();

const isInitialLoad = ref(true);
const isDateChanging = ref(false);
const pendingDestinationIds = ref<IdIsExternal[]>();

const isDepartureDisabled = ref(true);
const isDestinationDisabled = ref(true);

const effectiveDeparturePoints = computed(() =>
    headTruckModel.value ? truckDeparturePoints.value : departurePoints.value,
);

const effectiveDestinationPoints = computed(() =>
    tailTruckModel.value ? truckDestinationPoints.value : destinationPoints.value,
);

function submit(e: Event) {
    if (!calcForm.value!.checkValidity()) return;

    e.preventDefault();
    emit("calculate");
}

function setSelectedPoints(
    points: IPoint[],
    ids: IdIsExternal[],
): IdIsExternal[] | undefined {
    if (!ids.length)
        return undefined;

    let pointFound: IPoint | undefined;
    for (const selectedId of ids) {
        for (const point of points) {
            if (point.ids.includes(Number(selectedId.id)) || point.external_ids.includes(String(selectedId.id))) {
                pointFound = point;
                break;
            }

            for (const port of point.ports) {
                if (port.ids.includes(Number(selectedId.id)) || port.external_ids.includes(String(selectedId.id))) {
                    pointFound = point;
                    break;
                }
            }
            if (pointFound) break;
        }
        if (pointFound) break;
    }

    if (!pointFound)
        return undefined;

    let allIds: IdIsExternal[] = [
        ...pointFound.ids.map(id => ({ id, isExternal: false })),
        ...pointFound.external_ids.map(id => ({ id, isExternal: true })),
    ];

    for (const port of pointFound.ports)
        allIds = [
            ...allIds,
            ...port.ids.map(id => ({ id, isExternal: false })),
            ...port.external_ids.map(id => ({ id, isExternal: true })),
        ];

    return allIds.length ? allIds : undefined;
}

const isDateValid = () => (dateModel.value && !isNaN(new Date(dateModel.value).getDay()));

// Update departures on 'dateModel' changing — save/restore selections
watch(dateModel, async () => {
    if (isInitialLoad.value) return;

    if (!isDateValid()) return;

    const prevDepartureIds = departureIdsModel.value?.length ? [...departureIdsModel.value] : undefined;
    const prevDestinationIds = destinationIdsModel.value?.length ? [...destinationIdsModel.value] : undefined;

    isDateChanging.value = true;
    isDepartureDisabled.value = true;
    isDestinationDisabled.value = true;

    try {
        // 1. Fetch departures
        const depResponse = await getDepartures(dateModel.value!);
        departurePoints.value = depResponse.data;

        const truckDepResponse = await getTruckDepartures(dateModel.value!);
        truckDeparturePoints.value = truckDepResponse.data;

        isDepartureDisabled.value = !depResponse.data.length && !truckDepResponse.data.length;

        if (!depResponse.data.length && !truckDepResponse.data.length) {
            if (prevDepartureIds)
                useToast().show("Выбранные пункты отправления недоступны на выбранную дату", "warning");
            departureIdsModel.value = undefined;
            destinationPoints.value = [];
            truckDestinationPoints.value = [];
            destinationIdsModel.value = undefined;
            isDestinationDisabled.value = true;
            return;
        }

        // 2. Try to restore departure
        if (prevDepartureIds) {
            const depPool = headTruckModel.value ? truckDeparturePoints.value : departurePoints.value;
            const depFound = setSelectedPoints(depPool, prevDepartureIds);
            departureIdsModel.value = depFound ?? undefined;
            if (!depFound)
                useToast().show("Выбранные пункты отправления недоступны на выбранную дату", "warning");
        }

        // 3. Fetch destinations if departure is selected
        if (departureIdsModel.value?.length) {
            const destResponse = await getDestinations(dateModel.value!, departureIdsModel.value);
            destinationPoints.value = destResponse.data;

            const truckDestResponse = await getTruckDestinations(dateModel.value!);
            truckDestinationPoints.value = truckDestResponse.data;

            isDestinationDisabled.value = !destResponse.data.length && !truckDestResponse.data.length;

            if (!destResponse.data.length && !truckDestResponse.data.length) {
                if (prevDestinationIds)
                    useToast().show("Выбранные пункты прибытия недоступны на выбранную дату", "warning");
                destinationIdsModel.value = undefined;
                pendingDestinationIds.value = undefined;
                return;
            }

            // 4. Try to restore destination
            if (prevDestinationIds) {
                const destPool = tailTruckModel.value ? truckDestResponse.data : destResponse.data;
                const destFound = setSelectedPoints(destPool, prevDestinationIds);
                destinationIdsModel.value = destFound ?? undefined;
                if (!destFound)
                    useToast().show("Выбранные пункты прибытия недоступны на выбранную дату", "warning");
            }
        } else {
            destinationPoints.value = [];
            truckDestinationPoints.value = [];
            isDestinationDisabled.value = true;
            if (prevDepartureIds)
                destinationIdsModel.value = undefined;
            pendingDestinationIds.value = undefined;
        }
    } catch {
        useToast().show("Ошибка загрузки данных", "error");
    } finally {
        isDateChanging.value = false;
    }
});

// Update destinations on departure change — skip during date change
watch(departureIdsModel, async () => {
    if (isInitialLoad.value || isDateChanging.value) return;

    if (!departureIdsModel.value?.length) {
        if (destinationIdsModel.value?.length)
            pendingDestinationIds.value = [...destinationIdsModel.value];
        isDestinationDisabled.value = true;
        destinationPoints.value = [];
        return;
    }

    const prevDestinationIds = pendingDestinationIds.value;
    pendingDestinationIds.value = undefined;

    isDestinationDisabled.value = true;
    destinationIdsModel.value = undefined;
    destinationPoints.value = [];

    if (!isDateValid()) return;

    try {
        const response = await getDestinations(dateModel.value!, departureIdsModel.value);
        destinationPoints.value = response.data;

        const truckDestResponse = await getTruckDestinations(dateModel.value!);
        truckDestinationPoints.value = truckDestResponse.data;

        isDestinationDisabled.value = !response.data.length && !truckDestResponse.data.length;

        if (prevDestinationIds && (response.data.length || truckDestResponse.data.length)) {
            const destPool = tailTruckModel.value ? truckDestResponse.data : response.data;
            const destFound = setSelectedPoints(destPool, prevDestinationIds);
            destinationIdsModel.value = destFound ?? undefined;
            if (!destFound)
                useToast().show("Выбранные пункты прибытия недоступны для нового пункта отправления", "warning");
        }
    } catch {
        useToast().show("Ошибка загрузки данных", "error");
        isDestinationDisabled.value = false;
    }
});

// Clear pending destination when user manually clears it via ×
watch(destinationIdsModel, () => {
    if (isInitialLoad.value || isDateChanging.value) return;
    if (!departureIdsModel.value?.length && pendingDestinationIds.value?.length && !destinationIdsModel.value?.length)
        pendingDestinationIds.value = undefined;
});

// Load truck departure points when "From door" checkbox is activated
watch(headTruckModel, async (val) => {
    if (isInitialLoad.value) return;

    departureIdsModel.value = undefined;
    destinationIdsModel.value = undefined;
    destinationPoints.value = [];
    isDestinationDisabled.value = true;

    if (!isDateValid()) return;

    if (val && !truckDeparturePoints.value.length) {
        try {
            const response = await getTruckDepartures(dateModel.value!);
            truckDeparturePoints.value = response.data;
            if (!response.data.length)
                useToast().show("Пункты отгрузки от двери недоступны", "warning");
        } catch {
            useToast().show("Ошибка загрузки данных", "error");
        }
    }
});

// Load truck destination points when "To door" checkbox is activated
watch(tailTruckModel, async (val) => {
    if (isInitialLoad.value) return;

    destinationIdsModel.value = undefined;

    if (!isDateValid()) return;

    if (val && !truckDestinationPoints.value.length) {
        try {
            const response = await getTruckDestinations(dateModel.value!);
            truckDestinationPoints.value = response.data;
            if (!response.data.length)
                useToast().show("Пункты доставки до двери недоступны", "warning");
        } catch {
            useToast().show("Ошибка загрузки данных", "error");
        }
    }
});

const isCalculateDisabled = computed(() =>
    isDepartureDisabled.value ||
    isDestinationDisabled.value ||
    !departureIdsModel.value?.length ||
    !destinationIdsModel.value?.length
);

onMounted(async () => {
    if (!isDateValid()) {
        isInitialLoad.value = false;
        return;
    }

    // Block before loading
    isDepartureDisabled.value = true;
    isDestinationDisabled.value = true;
    // Save initial values
    const initialDepartureIds = departureIdsModel.value;
    const initialDestinationIds = destinationIdsModel.value;

    try {
        const depResponse = await getDepartures(dateModel.value!);
        departurePoints.value = depResponse.data;

        const truckDepResponse = await getTruckDepartures(dateModel.value!);
        truckDeparturePoints.value = truckDepResponse.data;

        isDepartureDisabled.value = false;

        // Restore selected departure if it is in URL
        if (initialDepartureIds && (departurePoints.value.length || truckDeparturePoints.value.length)) {
            const depPool = headTruckModel.value ? truckDeparturePoints.value : departurePoints.value;
            const depFound = setSelectedPoints(depPool, initialDepartureIds);
            departureIdsModel.value = depFound ?? undefined;
        } else departureIdsModel.value = undefined;

        // Load destinations if a departure is selected
        if (departureIdsModel.value) {
            const destResponse = await getDestinations(dateModel.value!, departureIdsModel.value);
            destinationPoints.value = destResponse.data;

            const truckDestResponse = await getTruckDestinations(dateModel.value!);
            truckDestinationPoints.value = truckDestResponse.data;

            isDestinationDisabled.value = false;

            // Restore selected destination if it is in URL
            if (initialDestinationIds && (destResponse.data.length || truckDestResponse.data.length)) {
                const destPool = tailTruckModel.value ? truckDestResponse.data : destResponse.data;
                const destFound = setSelectedPoints(destPool, initialDestinationIds);
                destinationIdsModel.value = destFound ?? undefined;
            } else destinationIdsModel.value = undefined;
        } else {
            destinationPoints.value = [];
            truckDestinationPoints.value = [];
            destinationIdsModel.value = undefined;
            isDestinationDisabled.value = true;
        }
    } catch {
        useToast().show("Ошибка загрузки данных", "error");
    } finally {
        isInitialLoad.value = false;
    }
});
</script>

<template>
    <form ref="calcForm">
        <div class="mb-3">
            <label :for="dateInputId" class="form-label">Дата отгрузки</label>
            <input
                type="date"
                class="form-control"
                :id="dateInputId"
                v-model="dateModel"
                value=""
                required
            />
        </div>

        <div class="mb-3 position-relative">
            <PointsSelect
                :points="effectiveDeparturePoints"
                text-label="Пункт отправления"
                v-model="departureIdsModel"
                v-model:is-disabled="isDepartureDisabled"
                v-model:search-text="departureInputText"
            />
            <div class="form-check">
                <input
                    class="form-check-input"
                    type="checkbox"
                    id="fromDoorCheck"
                    v-model="headTruckModel"
                />
                <label class="form-check-label" for="fromDoorCheck">От двери</label>
            </div>
        </div>

        <div class="mb-3 position-relative">
            <PointsSelect
                :points="effectiveDestinationPoints"
                text-label="Пункт прибытия"
                v-model="destinationIdsModel"
                v-model:is-disabled="isDestinationDisabled"
                v-model:search-text="destinationInputText"
            />
            <div class="form-check">
                <input
                    class="form-check-input"
                    type="checkbox"
                    id="toDoorCheck"
                    v-model="tailTruckModel"
                />
                <label class="form-check-label" for="toDoorCheck">До двери</label>
            </div>
        </div>

        <div class="mb-3">
            <label :for="containerTypeSelectId" class="form-label">Тип контейнера</label>
            <select
                class="form-select"
                :id="containerTypeSelectId"
                v-model="containerTypeModel"
                required
            >
                <option selected disabled value="">Выберите тип контейнера</option>
                <option value="20">20'DC</option>
                <option value="40">40'HC</option>
            </select>
        </div>

        <div class="md-3 row">
            <div class="col-md">
                <label :for="containerWeightInputId" class="form-label">Вес груза (т)</label>
                <input
                    type="number"
                    class="form-control"
                    :id="containerWeightInputId"
                    v-model="containerWeightModel"
                    min="1"
                    step="1"
                    max="28"
                    placeholder="Введите вес груза"
                    required
                />
            </div>
        </div>

        <p></p>
        <hr />

        <div class="md-3 row">
            <button type="submit" @click.stop="submit" :disabled="isCalculateDisabled" class="btn btn-primary col-md">
                Расcчитать
            </button>
            <button type="reset" @click.stop="$emit('reset')" class="btn btn-danger col-md">Очистить</button>
        </div>
    </form>
</template>
