<script setup lang="ts">
import BeautifulRatio from "@/components/BeautifulRatio.vue";
import type { IService } from "@/interfaces/Service";

import { ref, watch } from "vue";

const props = defineProps<{
    service: IService;
}>();

const emit = defineEmits(["update:checked"]);
const checked = ref<boolean>(props.service.checked);

watch(checked, (val: boolean) => emit("update:checked", val));
</script>

<template>
    <div class="row" :class="{ 'service-unchecked': !checked }">
        <div class="col-md-1 print-mode--hidden">
            <BeautifulRatio :is-disabled="service.mandatory" v-model="checked" />
        </div>
        <div class="col-md-6 service-name-col">
            <div>{{ service.name }}</div>
            <small v-if="service.description" class="text-muted">{{ service.description }}</small>
        </div>
        <div class="col-md-4 service-price-col text-end">
            <span>{{ service.price }} {{ service.currency }}</span>
        </div>
    </div>
</template>
