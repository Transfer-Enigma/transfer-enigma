<script setup lang="ts">
import type { IService } from "@/interfaces/Service";

import ServiceView from "@/components/ServiceView.vue";
import { computed, ref } from "vue";

const props = defineProps<{
    services: IService[];
}>();

defineEmits(["update:checked"]);

const isExpanded = ref<boolean>(false);
const isEmpty = computed<boolean>(() => {
    for (const service of props.services)
        if (service.checked) return false;

    return true;
});
</script>

<template>
    <div class="services-container border rounded p-3 mt-3" :class="{ empty: isEmpty }" v-if="services.length">
        <button
            @click="isExpanded = !isExpanded"
            class="btn btn-link p-0 mb-2 services-expand-btn"
        >
            {{ isExpanded ? "Свернуть список услуг" : "Развернуть список услуг" }}
        </button>

        <div class="services-content" v-show="isExpanded">
            <div v-for="(service, index) in services" :key="index" class="mb-2">
                <ServiceView :service="service" @update:checked="(val: boolean) => $emit('update:checked', val, index)" />
            </div>
        </div>
    </div>
</template>
