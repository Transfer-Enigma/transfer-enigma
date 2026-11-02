import { fetchAsJSON } from "@/helpers/requests";

interface RatesResponse {
    rates: Record<string, number>;
    updated_at: string;
}

export const getRates = async (): Promise<Record<string, number>> => {
    const { rates } = (await fetchAsJSON("/api/v2/rates")) as RatesResponse;
    return rates;
};
