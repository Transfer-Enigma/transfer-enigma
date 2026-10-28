import { API_ENDPOINTS } from "./ApiConfig";
import type {
    ICachePolicy,
    ICachePolicyPatch,
} from "@/interfaces/CachePolicy";
import axios from "axios";

const ROOT = API_ENDPOINTS.CACHE_POLICIES.ROOT;

export const listCachePolicies = async (
    source?: string,
    entity?: string,
): Promise<ICachePolicy[]> => {
    const params: Record<string, string> = {};
    if (source) params.source = source;
    if (entity) params.entity = entity;
    return (await axios.get(ROOT, { params, withCredentials: true })).data;
};

export const getCachePolicy = async (id: number): Promise<ICachePolicy> =>
    (await axios.get(API_ENDPOINTS.CACHE_POLICIES.byId(id), {
        withCredentials: true,
    })).data;

export const updateCachePolicy = async (
    id: number,
    payload: ICachePolicyPatch,
): Promise<ICachePolicy> =>
    (await axios.patch(API_ENDPOINTS.CACHE_POLICIES.byId(id), payload, {
        withCredentials: true,
    })).data;

export const invalidateCachePolicy = async (id: number): Promise<number> =>
    (await axios.post(
        API_ENDPOINTS.CACHE_POLICIES.invalidateById(id),
        null,
        { withCredentials: true },
    )).data.deleted;

export const invalidateAllCachePolicies = async (): Promise<number> =>
    (await axios.post(
        API_ENDPOINTS.CACHE_POLICIES.invalidate(),
        null,
        { withCredentials: true },
    )).data.deleted;
