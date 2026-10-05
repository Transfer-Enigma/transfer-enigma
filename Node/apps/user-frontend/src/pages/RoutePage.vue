<script setup lang="ts">
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import ResultsWidget from "@/widgets/ResultsWidget.vue";

import { getRouteDetail, getRouteDetailWithoutMarkup } from "@/api_helpers/routes";
import { useToast } from "@/composables/useToast";
import { processRoutes } from "@/services/calculator";
import { updateUser } from "@/services/auth";
import { loadCachedRates, updateRates } from "@/services/rates";

import { computed, onMounted, ref } from "vue";

import type { RouteDescriptor, RouteExtendedDescriptor } from "@/interfaces/Routes";

interface Props {
    segments?: string;
    includedServices?: string;
    demo: boolean;
}

const props = defineProps<Props>();

const loading = ref<boolean>(true);
const notFound = ref<boolean>(false);
const unauthorized = ref<boolean>(false);
const errorMessage = ref<string | undefined>();
const markupRoutes = ref<RouteExtendedDescriptor[] | undefined>();
const baseRoutes = ref<RouteExtendedDescriptor[] | undefined>();
const baseLoaded = ref<boolean>(false);
const baseFailed = ref<boolean>(false);
const showWithoutMarkup = ref<boolean>(false);
const isLoggedIn = ref<boolean>(false);

const canToggleMarkup = computed(() => props.demo && isLoggedIn.value);
const displayedRoutes = computed(() => showWithoutMarkup.value ? baseRoutes.value : markupRoutes.value);

function statusOf(e: unknown): number | null {
    const match = /\[(\d{3})\]/.exec((e as Error)?.message ?? "");
    return match?.[1] ? Number(match[1]) : null;
}

async function load() {
    try {
        loadCachedRates();
        await updateRates();

        if (!props.segments) {
            notFound.value = true;
            return;
        }

        const descriptor: RouteDescriptor = props.demo
            ? await getRouteDetail(props.segments, props.includedServices)
            : await getRouteDetailWithoutMarkup(props.segments, props.includedServices);
        markupRoutes.value = processRoutes([descriptor], false);
    } catch (e) {
        const status = statusOf(e);
        if (status === 404 || !props.segments)
            notFound.value = true;
        else if (status === 401)
            unauthorized.value = true;
        else
            errorMessage.value = (e as Error)?.message ?? "Неизвестная ошибка";
    } finally {
        loading.value = false;
    }

    try {
        await updateUser();
        isLoggedIn.value = true;
    } catch {
        isLoggedIn.value = false;
    }
}

async function toggleMarkup() {
    showWithoutMarkup.value = !showWithoutMarkup.value;

    if (showWithoutMarkup.value && !baseLoaded.value) {
        try {
            const descriptor = await getRouteDetailWithoutMarkup(props.segments!, props.includedServices);
            baseRoutes.value = processRoutes([descriptor], false);
            baseLoaded.value = true;
        } catch (e) {
            console.log(e);
            baseFailed.value = true;
            showWithoutMarkup.value = false;
            useToast().show("Не удалось загрузить цену без надбавки", "error");
        }
    }
}

onMounted(load);
</script>

<template>
    <div class="my-5">
        <h2 class="mb-4 text-center">Маршрут</h2>

        <div class="text-center" v-if="loading"><LoadingSpinner /></div>

        <div v-else-if="notFound" class="container py-5 text-center">
            <h1>404</h1>
            <p class="lead">Маршрут не найден</p>
            <router-link to="/" class="btn btn-primary">На главную</router-link>
        </div>

        <div v-else-if="unauthorized" class="container py-5 text-center">
            <p class="lead">Войдите, чтобы посмотреть маршрут</p>
            <router-link to="/login" class="btn btn-primary">Войти</router-link>
        </div>

        <div v-else-if="errorMessage" class="alert alert-danger">{{ errorMessage }}</div>

        <div v-else-if="displayedRoutes">
            <div v-if="canToggleMarkup" class="mb-3">
                <button class="btn btn-secondary" @click="toggleMarkup">
                    <template v-if="showWithoutMarkup">
                        Показать цену с надбавкой
                    </template>
                    <template v-else>
                        Показать цену без надбавки
                    </template>
                </button>
            </div>

            <div v-if="baseFailed" class="alert alert-warning">Не удалось загрузить цену без надбавки</div>

            <ResultsWidget :routes="displayedRoutes" />
        </div>
    </div>
</template>
