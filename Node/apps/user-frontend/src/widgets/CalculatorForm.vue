<script setup lang="ts">
import type { IPoint, IPointIds, IdIsExternal } from "@/interfaces/Point";
import PointsSelect from "@/widgets/PointsSelect.vue";

import { getDepartures, getDestinations, getTruckDepartures, getTruckDestinations } from "@/api_helpers/points";
import { useToast } from "@/composables/useToast";
import { computed, onMounted, ref, useId, watch } from "vue";

const dateModel = defineModel<string>("date");
const departureIdsModel = defineModel<IdIsExternal[]>("departure");
const destinationIdsModel = defineModel<IdIsExternal[]>("destination");
const containerTypeModel = defineModel<string>("containerType");
const containerWeightModel = defineModel<number>("containerWeight");
const truckStartModel = defineModel<IdIsExternal[]>("truckStart");
const truckEndModel = defineModel<IdIsExternal[]>("truckEnd");

const departureInputDisabledModel = defineModel<boolean>("isDepartureDisabled", { required: false, default: true });
const destinationInputDisabledModel = defineModel<boolean>("isDestinationDisabled", { required: false, default: true });

const departureInputTextModel = defineModel<string>("departureSearchText", { required: false, default: "" });
const destinationInputTextModel = defineModel<string>("destinationSearchText", { required: false, default: "" });

const emit = defineEmits(["calculate", "reset"]);

const dateInputId = useId();
const containerTypeSelectId = useId();
const containerWeightInputId = useId();

const departurePoints = ref<IPoint[]>([]);
const destinationPoints = ref<IPoint[]>([]);
const truckDeparturePoints = ref<IPoint[]>([]);
const truckDestinationPoints = ref<IPoint[]>([]);
const calcForm = ref<HTMLFormElement>();

const isInitialLoad = ref(true);
const isDateChanging = ref(false);
const pendingDestinationIds = ref<IdIsExternal[]>();

const isFromDoor = ref<boolean>(!!truckStartModel.value?.length);
const isToDoor = ref<boolean>(!!truckEndModel.value?.length);

const truckStartDisabled = ref(true);
const truckEndDisabled = ref(true);

function submit(e: Event) {
    if (!calcForm.value!.checkValidity()) return;

    e.preventDefault();
    emit("calculate");
}

function idMatches(entity: IPointIds, selectedId: IdIsExternal): boolean {
    return entity.ids.includes(Number(selectedId.id)) || entity.external_ids.includes(String(selectedId.id));
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
            if (idMatches(point, selectedId)) {
                pointFound = point;
                break;
            }

            for (const port of point.ports) {
                if (idMatches(port, selectedId)) {
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
    departureInputDisabledModel.value = true;
    destinationInputDisabledModel.value = true;

    try {
        // 1. Fetch departures
        const depResponse = await getDepartures(dateModel.value!);
        const { data: depData } = depResponse;
        departurePoints.value = depData;
        departureInputDisabledModel.value = !depData.length;

        if (!depData.length) {
            if (prevDepartureIds)
                useToast().show("Выбранные пункты отправления недоступны на выбранную дату", "warning");
            departureIdsModel.value = undefined;
            destinationPoints.value = [];
            destinationIdsModel.value = undefined;
            destinationInputDisabledModel.value = true;
            return;
        }

        // 2. Try to restore departure
        if (prevDepartureIds) {
            const depFound = setSelectedPoints(depData, prevDepartureIds);
            departureIdsModel.value = depFound ?? undefined;
            if (!depFound)
                useToast().show("Выбранные пункты отправления недоступны на выбранную дату", "warning");
        }

        // 3. Fetch destinations if departure is selected
        if (departureIdsModel.value?.length) {
            const destResponse = await getDestinations(dateModel.value!, departureIdsModel.value);
            const { data: destData } = destResponse;
            destinationPoints.value = destData;
            destinationInputDisabledModel.value = !destData.length;

            if (!destData.length) {
                if (prevDestinationIds)
                    useToast().show("Выбранные пункты прибытия недоступны на выбранную дату", "warning");
                destinationIdsModel.value = undefined;
                pendingDestinationIds.value = undefined;
                return;
            }

            // 4. Try to restore destination
            if (prevDestinationIds) {
                const destFound = setSelectedPoints(destData, prevDestinationIds);
                destinationIdsModel.value = destFound ?? undefined;
                if (!destFound)
                    useToast().show("Выбранные пункты прибытия недоступны на выбранную дату", "warning");
            }
        } else {
            destinationPoints.value = [];
            destinationInputDisabledModel.value = true;
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
        destinationInputDisabledModel.value = true;
        destinationPoints.value = [];
        return;
    }

    const prevDestinationIds = pendingDestinationIds.value;
    pendingDestinationIds.value = undefined;

    destinationInputDisabledModel.value = true;
    destinationIdsModel.value = undefined;
    destinationPoints.value = [];

    if (!isDateValid()) return;

    try {
        const response = await getDestinations(dateModel.value!, departureIdsModel.value);
        const { data } = response;
        destinationPoints.value = data;
        destinationInputDisabledModel.value = !data.length;

        if (prevDestinationIds && data.length) {
            const destFound = setSelectedPoints(data, prevDestinationIds);
            destinationIdsModel.value = destFound ?? undefined;
            if (!destFound)
                useToast().show("Выбранные пункты прибытия недоступны для нового пункта отправления", "warning");
        }
    } catch {
        useToast().show("Ошибка загрузки данных", "error");
        destinationInputDisabledModel.value = false;
    }
});

// Clear pending destination when user manually clears it via ×
watch(destinationIdsModel, () => {
    if (isInitialLoad.value || isDateChanging.value) return;
    if (!departureIdsModel.value?.length && pendingDestinationIds.value?.length && !destinationIdsModel.value?.length)
        pendingDestinationIds.value = undefined;
});

// Load truck departure points when "From door" checkbox is activated
watch(isFromDoor, async (val) => {
    if (!val) {
        truckStartModel.value = undefined;
        return;
    }
    if (!isDateValid()) return;

    truckStartDisabled.value = true;
    try {
        const response = await getTruckDepartures(dateModel.value!);
        truckDeparturePoints.value = response.data;
        truckStartDisabled.value = !response.data.length;
        if (!response.data.length)
            useToast().show("Пункты отгрузки от двери недоступны", "warning");
    } catch {
        useToast().show("Ошибка загрузки данных", "error");
    }
});

// Load truck destination points when "To door" checkbox is activated
watch(isToDoor, async (val) => {
    if (!val) {
        truckEndModel.value = undefined;
        return;
    }
    if (!isDateValid()) return;

    truckEndDisabled.value = true;
    try {
        const response = await getTruckDestinations(dateModel.value!);
        truckDestinationPoints.value = response.data;
        truckEndDisabled.value = !response.data.length;
        if (!response.data.length)
            useToast().show("Пункты доставки до двери недоступны", "warning");
    } catch {
        useToast().show("Ошибка загрузки данных", "error");
    }
});

// Reload truck points when date changes
watch(dateModel, () => {
    if (isInitialLoad.value) return;

    if (isFromDoor.value) {
        truckStartModel.value = undefined;
        truckDeparturePoints.value = [];
        isFromDoor.value = false;
    }
    if (isToDoor.value) {
        truckEndModel.value = undefined;
        truckDestinationPoints.value = [];
        isToDoor.value = false;
    }
});

const isCalculateDisabled = computed(() =>
    departureInputDisabledModel.value ||
    destinationInputDisabledModel.value ||
    !departureIdsModel.value?.length ||
    !destinationIdsModel.value?.length
);

onMounted(async () => {
    if (!isDateValid()) {
        isInitialLoad.value = false;
        return;
    }

    // Block before loading
    departureInputDisabledModel.value = true;
    destinationInputDisabledModel.value = true;
    // Save initial values
    const initialDepartureIds = departureIdsModel.value;
    const initialDestinationIds = destinationIdsModel.value;
    const initialTruckStartIds = truckStartModel.value;
    const initialTruckEndIds = truckEndModel.value;

    try {
        const depResponse = await getDepartures(dateModel.value!);
        departurePoints.value = depResponse.data;
        departureInputDisabledModel.value = false;

        // Restore selected departure if it is in URL
        if (initialDepartureIds && departurePoints.value.length) {
            const depFound = setSelectedPoints(departurePoints.value, initialDepartureIds);
            departureIdsModel.value = depFound ?? undefined;
        } else departureIdsModel.value = undefined;

        // Load destinations if a departure is selected
        if (departureIdsModel.value) {
            const destResponse = await getDestinations(dateModel.value!, departureIdsModel.value);
            const { data: destData } = destResponse;
            destinationPoints.value = destData;
            destinationInputDisabledModel.value = false;

            // Restore selected destination if it is in URL
            if (initialDestinationIds && destData.length) {
                const destFound = setSelectedPoints(destData, initialDestinationIds);
                destinationIdsModel.value = destFound ?? undefined;
            } else destinationIdsModel.value = undefined;
        } else {
            destinationPoints.value = [];
            destinationIdsModel.value = undefined;
            destinationInputDisabledModel.value = true;
        }

        // Restore truck start from URL
        if (initialTruckStartIds?.length) {
            isFromDoor.value = true;
            const truckStartResponse = await getTruckDepartures(dateModel.value!);
            truckDeparturePoints.value = truckStartResponse.data;
            truckStartDisabled.value = false;
            const found = setSelectedPoints(truckStartResponse.data, initialTruckStartIds);
            truckStartModel.value = found ?? undefined;
        }

        // Restore truck end from URL
        if (initialTruckEndIds?.length) {
            isToDoor.value = true;
            const truckEndResponse = await getTruckDestinations(dateModel.value!);
            truckDestinationPoints.value = truckEndResponse.data;
            truckEndDisabled.value = false;
            const found = setSelectedPoints(truckEndResponse.data, initialTruckEndIds);
            truckEndModel.value = found ?? undefined;
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
                :points="departurePoints"
                text-label="Пункт отправления"
                v-model="departureIdsModel"
                v-model:is-disabled="departureInputDisabledModel"
                v-model:search-text="departureInputTextModel"
            />
            <div class="form-check">
                <input
                    class="form-check-input"
                    type="checkbox"
                    id="fromDoorCheck"
                    v-model="isFromDoor"
                />
                <label class="form-check-label" for="fromDoorCheck">От двери</label>
            </div>
            <PointsSelect
                v-if="isFromDoor"
                :points="truckDeparturePoints"
                text-label="Пункт доставки от двери"
                v-model="truckStartModel"
                v-model:is-disabled="truckStartDisabled"
            />
        </div>

        <div class="mb-3 position-relative">
            <PointsSelect
                :points="destinationPoints"
                text-label="Пункт прибытия"
                v-model="destinationIdsModel"
                v-model:is-disabled="destinationInputDisabledModel"
                v-model:search-text="destinationInputTextModel"
            />
            <div class="form-check">
                <input
                    class="form-check-input"
                    type="checkbox"
                    id="toDoorCheck"
                    v-model="isToDoor"
                />
                <label class="form-check-label" for="toDoorCheck">До двери</label>
            </div>
            <PointsSelect
                v-if="isToDoor"
                :points="truckDestinationPoints"
                text-label="Пункт доставки до двери"
                v-model="truckEndModel"
                v-model:is-disabled="truckEndDisabled"
            />
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
