import { API_ENDPOINTS } from "./ApiConfig";
import { SyncDocument } from "@/interfaces/Data";
import axios from "axios";

export const listSyncDocuments = async (): Promise<SyncDocument[]> =>
    (await axios.get(
        `${API_ENDPOINTS.SYNC_DOCUMENTS.ROOT}`,
        { withCredentials: true },
    )).data;

export const deleteSyncDocument = async (id: number): Promise<void> => {
    await axios.delete(
        `${API_ENDPOINTS.SYNC_DOCUMENTS.byId(id)}`,
        { withCredentials: true },
    );
};

export interface SheetsPreview {
    sheets: string[];
    suggested_mapping: Record<string, string | null>;
}

export const previewDocumentSheets = async (url: string): Promise<SheetsPreview> =>
    (await axios.get(
        `${API_ENDPOINTS.SYNC_DOCUMENTS.SHEETS_PREVIEW}`,
        { params: { url }, withCredentials: true },
    )).data;

export const createSyncDocument = async (payload: Partial<SyncDocument>): Promise<SyncDocument> =>
    (await axios.post(
        `${API_ENDPOINTS.SYNC_DOCUMENTS.ROOT}`,
        payload,
        { withCredentials: true },
    )).data;

export const patchSyncDocument = async (id: number, payload: Partial<SyncDocument>): Promise<SyncDocument> =>
    (await axios.patch(
        `${API_ENDPOINTS.SYNC_DOCUMENTS.byId(id)}`,
        payload,
        { withCredentials: true },
    )).data;
