<script setup lang="ts">
import { getCurrencySymbol } from "@/helpers/currency";
import { computed, inject, ref, watch } from "vue";

import type { Ref } from "vue";

const props = defineProps<{
    price: number,
    currency: string,
}>();

const editable: Ref<boolean> = inject("editable", ref(false));

const currencySymbol = computed(
    () => getCurrencySymbol(props.currency)
);

defineEmits(["update:price"]);

const priceRef = ref<number>(props.price);

const numberFormatter = new Intl.NumberFormat();
const fp = (price: number) => numberFormatter.format(price);

watch(() => props.price, (newPrice: number) => (priceRef.value = newPrice));
</script>

<template>
    <span v-if="currencySymbol && price >= 0">
        {{ currencySymbol }}
    </span>

    <input v-if="editable" v-model="priceRef" @blur="$emit('update:price', priceRef)" type="number">
    <span v-else>{{ fp(price) }}</span>

    <span v-if="!currencySymbol">
        &nbsp;
        {{ currency }}
    </span>
    <span v-else-if="currencySymbol && price < 0">
        {{ currencySymbol }}
    </span>
</template>
