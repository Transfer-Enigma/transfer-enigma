<script setup lang="ts">
import type { IdIsExternal, IPoint } from "@/interfaces/Point";

import SelectWithFilter from "@/components/SelectWithFilter.vue";

import { useBlurredFields } from "@/composables/useBlurredFields";
import { useLang } from "@/stores/lang";
import { computed } from "vue";

interface Props {
    points: IPoint[];
    textLabel: string;
    clearSignal?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    clearSignal: false,
});

const selectedPointModel = defineModel<IdIsExternal[] | undefined>({ required: false });
const searchTextModel = defineModel<string>("searchText", { required: false, default: "" });
const isDisabledModel = defineModel<boolean>("isDisabled", { required: false, default: false });

defineEmits(["update:clearSignal"]);

const { lang } = useLang();
const { isFieldBlurred } = useBlurredFields();

const pointOptions = computed(() =>
    props.points?.map((point: IPoint) => {
        let companiesString = "";
        if (!isFieldBlurred("company")) {
            const seen = new Set<number>();
            const names: string[] = [];
            for (const c of point.companies)
                if (!seen.has(c.id)) {
                    seen.add(c.id);
                    names.push(c.name);
                }

            for (const port of point.ports)
                for (const c of port.companies)
                    if (!seen.has(c.id)) {
                        seen.add(c.id);
                        names.push(c.name);
                    }

            companiesString = names.join(",");
        }

        let ids: IdIsExternal[] = [
            ...point.ids.map(id => ({ id, isExternal: false })),
            ...point.external_ids.map(id => ({ id, isExternal: true })),
        ];

        for (const port of point.ports) ids = [
            ...ids,
            ...port.ids.map(id => ({ id, isExternal: false })),
            ...port.external_ids.map(id => ({ id, isExternal: true })),
        ];

        const translate = point.translates[lang];
        if (!translate) {
            console.warn(`Translation to ${lang} for points [${ids.join(", ")}] not found`);
            return;
        }

        const pointName = `${translate.country}, ${translate.name}`;
        const label = companiesString ? `${pointName} [${companiesString}]` : pointName;

        return { value: ids, label };
    }).filter(i => !!i)
);
</script>

<template>
    <SelectWithFilter
        v-model="selectedPointModel"
        v-model:search-text="searchTextModel"
        :key-fn="option => option.value.map(idDescriptor => idDescriptor.id).join(',')"
        :options="pointOptions"
        :label="textLabel"
        :placeholder="textLabel"
        :disabled="isDisabledModel"
        @update:clear-signal="$emit('update:clearSignal')"
        required
    />
</template>
