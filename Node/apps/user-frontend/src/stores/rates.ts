import { computed, reactive, ref } from "vue";
import { defineStore } from "pinia";

export type RatesMap = Map<string, number>;
export type RatesObject = Record<string, number>;

export const useRates = defineStore("rates", () => {
    const rates = reactive<RatesMap>(new Map());
    const currentRate = ref<string>("");
    let locker: Promise<void> | undefined;

    const setRates = (newRates: RatesObject) => {
        rates.clear();
        for (const [currency, value] of Object.entries(newRates))
            rates.set(currency.toUpperCase(), value);
    };

    const setCurrentRate = (newCurrentRate: string) => {
        if (!rates.size) throw new Error("Rates are not set");

        const normalized = newCurrentRate.toUpperCase();

        if (!rates.get(normalized)) throw new Error(`Undefined rate: "${newCurrentRate}"`);

        currentRate.value = normalized;
    };

    const setLocker = (newLocker: Promise<void>) => { locker = newLocker };
    const getLocker = () => locker;

    const currentRateValue = computed(() =>
        rates && currentRate.value ? rates.get(currentRate.value) : undefined
    );

    return { rates, currentRate, setRates, setCurrentRate, currentRateValue, setLocker, getLocker };
});
