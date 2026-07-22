<script setup lang="ts">
import type {
    RouteExtendedDescriptor,
    IMultiPriceSegment,
    ISinglePriceSegment, PriceRange
} from "@/interfaces/Routes";

import MultiPriceSegment from "@/components/routes/MultiPriceSegment.vue";
import SinglePriceSegment from "@/components/routes/SinglePriceSegment.vue";
import PriceWithCurrency from "@/components/PriceWithCurrency.vue";

import { useRates } from "@/stores/rates";
import { computed, inject, nextTick, ref, watch } from "vue";

import type { Ref } from "vue";
import ServicesView from "@/components/ServicesView.vue";

const props = defineProps<{
    route: RouteExtendedDescriptor,
}>();

const emit = defineEmits(["update:singlePrice", "update:multiPrice", "update:serviceChecked", "setSelected"]);

const ratesStore = useRates();
const currentRate = computed((): string => ratesStore.currentRate);

const segments = computed(
    () => props.route[0][0]
);
const drop = computed(
    () => props.route[0][1]
);

const editMode: Ref<boolean> = inject("editable") || ref(false);
const allRoutesSelected: Ref<boolean> = inject("allRoutesSelected") || ref(false);
const allRoutesSelectedSignalRef: Ref<boolean> = inject("allRoutesSelectedSignal") || ref(false);
const isDemoModeActive: Ref<boolean> = inject("isDemoModeActive") || ref(false);
const routeSelected = ref<boolean>(props.route[1][2]);

let quiteSelect: boolean = false;

watch(routeSelected, (newVal: boolean) => {
    if (quiteSelect) return;

    emit("setSelected", newVal);
});

watch(() => props.route, async (newRoute: RouteExtendedDescriptor) => {
    quiteSelect = true;
    routeSelected.value = newRoute[1][2];

    await nextTick();
    quiteSelect = false;
});

watch(allRoutesSelectedSignalRef, () => (routeSelected.value = allRoutesSelected.value));
</script>

<template>
    <div class="p-3 mb-4 border rounded shadow-sm result-item" :class="isDemoModeActive ? '' : routeSelected ? 'included' : 'excluded'">
        <label v-if="editMode"><input type="checkbox" v-model="routeSelected" class="select-route-checkbox"></label>
        <b v-else-if="!isDemoModeActive && !routeSelected">Маршрут не будет отображаться в КП</b>

        <div v-if="props.route[0][2]" class="alert alert-warning d-flex align-items-center" role="alert">
            <svg class="flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Warning:"><use xlink:href="#exclamation-triangle-fill"/></svg>
            <div>
                Маршрут может быть неактуален
            </div>
        </div>

        <div class="segments row">
            <div class="segment col-md m-2" :key="i" v-for="(segment, i) in segments">
                <div class="row">
                    <div class="col-md-11">
                        <SinglePriceSegment
                            :segment="segment as ISinglePriceSegment"
                            v-if="(segment as ISinglePriceSegment).price"
                            @update:price="(val: number) => $emit('update:singlePrice', val, i)"
                        />
                        <MultiPriceSegment
                            :segment="segment as IMultiPriceSegment"
                            v-else
                            @update:price="([val, priceIndex]) => $emit('update:multiPrice', val, priceIndex, i)"
                        />
                    </div>
                    <div class="col-md-1 segments-divider" v-if="i < segments.length - 1">
                        <span class="d-md-inline">&rightarrow;</span>
                        <span class="d-md-none">&downarrow;</span>
                    </div>
                </div>
            </div>
        </div>

        <hr>

        <div class="drop-off row">
            <div class="col-md-7">Drop off:</div>
            <div class="col-md-5">
                <span v-if="drop?.price">
                    <b><PriceWithCurrency :price="drop.price" :currency="drop.currency" /></b>
                    <span v-if="drop.conversation_percents" class="text-muted drop-off-conversation">
                        + {{ drop.conversation_percents }}% конвертация в рубли
                    </span>
                </span>
                <b v-else>включен</b>
            </div>
        </div>

        <hr>

        <ServicesView
            v-if="route[0][3]?.length"
            :services="route[0][3]"
            @update:checked="(val: boolean, serviceIndex: number) => $emit('update:serviceChecked', val, serviceIndex)"
        />

        <hr>

        <div class="row">
            <div class="col-md-7">
                Суммарная стоимость в валюте запроса:
            </div>
            <div class="col-md-5">
                <b v-if="Number.isNaN(route[1][0])">
                    <PriceWithCurrency :price="(route[1][0] as PriceRange)[0]" :currency="currentRate" />
                    &nbsp;&ndash;&nbsp;
                    <PriceWithCurrency :price="(route[1][0] as PriceRange)[1]" :currency="currentRate" />
                </b>
                <b v-else>
                    <PriceWithCurrency :price="route[1][0] as number" :currency="currentRate" />
                </b>
            </div>

            <div class="col-md-7">
                В рублях по курсу ЦБ на дату выставления счёта с учётом конвертации:
            </div>
            <div class="col-md-5">
                <b v-if="Number.isNaN(route[1][1])">
                    <PriceWithCurrency :price="(route[1][1] as PriceRange)[0]" :currency="currentRate" />
                    -
                    <PriceWithCurrency :price="(route[1][1] as PriceRange)[1]" :currency="currentRate" />
                </b>
                <b v-else>
                    <PriceWithCurrency :price="route[1][1] as number" :currency="currentRate" />
                </b>
            </div>
        </div>
    </div>
</template>

<style scoped>
.segments-divider {
    font-size: xx-large;

    display: flex;
    align-items: center;
    justify-content: center;

    & > .d-md-inline {
        display: none;
    }
}

.select-route-checkbox {
    width: 1.25rem;
    height: 1.25rem;
}

@media not print {
    .excluded {
        border-left: .5rem solid red !important;
    }

    .included {
        border-left: .5rem solid green !important;
    }
}
</style>
