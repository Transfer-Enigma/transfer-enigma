import { getRates } from "@/api_helpers/rates";
import { useToast } from "@/composables/useToast";
import { useRates } from "@/stores/rates";

const CACHED_RATES_KEY = "cached_rates";
const CACHED_RATES_DATE_KEY = "cached_rates_date";

export function loadCachedRates() {
    const { setRates, setCurrentRate } = useRates();
    try {
        const cached = localStorage.getItem(CACHED_RATES_KEY);
        const cachedDate = localStorage.getItem(CACHED_RATES_DATE_KEY);
        if (cached && cachedDate) {
            setRates(JSON.parse(cached) as Record<string, number>);
            if (!useRates().currentRate) setCurrentRate("RUB");
        }
    } catch {
        localStorage.removeItem(CACHED_RATES_KEY);
        localStorage.removeItem(CACHED_RATES_DATE_KEY);
    }
}

export async function updateRates() {
    const { setRates, setCurrentRate } = useRates();
    try {
        const rates = await getRates();
        setRates(rates);
        localStorage.setItem(CACHED_RATES_KEY, JSON.stringify(rates));
        localStorage.setItem(CACHED_RATES_DATE_KEY, new Date().toISOString().split("T")[0]!);
        if (!useRates().currentRate) setCurrentRate("RUB");
    } catch {
        const cachedDate = localStorage.getItem(CACHED_RATES_DATE_KEY);
        if (cachedDate) {
            useToast().show(
                `Невозможно получить актуальный курс валют. Показан курс на ${cachedDate}`,
                "warning",
                8000,
            );
        }
    }
}

export const lockRates = async (coro: Promise<void>) => useRates().setLocker(coro);

export const isConversationNeeded = (currency: string) =>
    ["RUB", "RUR", "РУБ"].indexOf(currency.toUpperCase()) === -1;

export function convertToCurrentRate(value: number, fromCurrency: string, percents?: number): [number, number] {
    const { rates, currentRateValue } = useRates();
    if (!currentRateValue) throw new Error("No current rate selected!");

    const fromRate = rates.get(fromCurrency.toUpperCase());
    if (!fromRate) throw new Error(`Invalid currency: ${fromCurrency}`);

    const result = value / currentRateValue * fromRate;

    percents = isConversationNeeded(fromCurrency) ? percents ?? 0 : 0;
    const resultWithConv = result * (1 + percents / 100);

    return [result, resultWithConv];
}
