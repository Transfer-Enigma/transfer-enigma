import { API_ENDPOINTS } from "./ApiConfig";
import type {
    ICachePolicy,
    ICachePolicyPatch,
    ICachePolicyPayload,
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

export const createCachePolicy = async (
    payload: ICachePolicyPayload,
): Promise<ICachePolicy> =>
    (await axios.post(ROOT, payload, { withCredentials: true })).data;

export const updateCachePolicy = async (
    id: number,
    payload: ICachePolicyPatch,
): Promise<ICachePolicy> =>
    (await axios.patch(API_ENDPOINTS.CACHE_POLICIES.byId(id), payload, {
        withCredentials: true,
    })).data;

export const deleteCachePolicy = async (id: number): Promise<void> =>
    await axios.delete(API_ENDPOINTS.CACHE_POLICIES.byId(id), {
        withCredentials: true,
    });

export const invalidateCachePolicies = async (entity?: string): Promise<void> => {
    const url = entity
        ? API_ENDPOINTS.CACHE_POLICIES.invalidateEntity(entity)
        : API_ENDPOINTS.CACHE_POLICIES.invalidate();
    await axios.post(url, null, { withCredentials: true });
};
