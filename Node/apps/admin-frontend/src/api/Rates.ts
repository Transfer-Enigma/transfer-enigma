import { API_ENDPOINTS } from "./ApiConfig";
import type { IRate, IRatePayload } from "@/interfaces/Rate";
import axios from "axios";

export const listRates = async (): Promise<IRate[]> =>
    (await axios.get(API_ENDPOINTS.RATES.ROOT, { withCredentials: true })).data;

export const getRate = async (id: number): Promise<IRate> =>
    (await axios.get(API_ENDPOINTS.RATES.byId(id), { withCredentials: true })).data;

export const createRate = async (payload: IRatePayload): Promise<IRate> =>
    (await axios.post(API_ENDPOINTS.RATES.ROOT, payload, { withCredentials: true })).data;

export const updateRate = async (id: number, payload: IRatePayload): Promise<IRate> =>
    (await axios.put(API_ENDPOINTS.RATES.byId(id), payload, { withCredentials: true })).data;

export const deleteRate = async (id: number): Promise<void> =>
    await axios.delete(API_ENDPOINTS.RATES.byId(id), { withCredentials: true });
