import { API_ENDPOINTS } from "./ApiConfig";
import { UpdateResponse, ValidateResponse } from "@/interfaces/Data";
import axios from "axios";

export interface RunParams {
    document_id?: number;
    load_on_warnings?: boolean;
    mode?: "all" | "new";
    fix?: boolean;
    highlight?: boolean;
    ensure_uids?: boolean;
    sheets?: string[];
}

export const updateFromGsheets = async (): Promise<UpdateResponse> =>
    (await axios.post(
        `${API_ENDPOINTS.DATA.UPDATE_FROM_GSHEETS}`,
        null,
        { withCredentials: true },
    )).data;

export const syncDocument = async (params: RunParams, file?: File): Promise<UpdateResponse> => {
    if (!file)
        return (await axios.post(
            `${API_ENDPOINTS.DATA.UPDATE_FROM_GSHEETS}`,
            null,
            { params, withCredentials: true },
        )).data;
    const formData = new FormData();
    formData.append("data_file", file);
    return (await axios.post(
        `${API_ENDPOINTS.DATA.UPDATE_FROM_GSHEETS}`,
        formData,
        {
            params,
            headers: { "Content-Type": "multipart/form-data" },
            withCredentials: true,
        },
    )).data;
};

export const validateDocument = async (params: RunParams, file?: File): Promise<ValidateResponse> => {
    if (!file)
        return (await axios.post(
            `${API_ENDPOINTS.DATA.VALIDATE_FROM_GSHEETS}`,
            null,
            { params, withCredentials: true },
        )).data;
    const formData = new FormData();
    formData.append("data_file", file);
    return (await axios.post(
        `${API_ENDPOINTS.DATA.VALIDATE_FROM_GSHEETS}`,
        formData,
        {
            params,
            headers: { "Content-Type": "multipart/form-data" },
            withCredentials: true,
        },
    )).data;
};

export const downloadValidatedFile = async (params: RunParams, file: File, filename: string): Promise<void> => {
    const formData = new FormData();
    formData.append("data_file", file);
    const response = await axios.post(
        `${API_ENDPOINTS.DATA.VALIDATE_FROM_GSHEETS}`,
        formData,
        {
            params: { ...params, artifact: "file" },
            headers: { "Content-Type": "multipart/form-data" },
            withCredentials: true,
            responseType: "blob",
        },
    );
    const url = window.URL.createObjectURL(new Blob([ response.data ]));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    window.URL.revokeObjectURL(url);
};

export async function updateFromFile(file: File): Promise<UpdateResponse> {
    const formData = new FormData();
    formData.append("data_file", file);

    return (await axios.post(
        `${API_ENDPOINTS.DATA.UPDATE_FROM_GSHEETS}`,
        formData,
        {
            headers: { "Content-Type": "multipart/form-data" },
            withCredentials: true,
        },
    )).data;
}

export const deleteAllData = async (): Promise<void> =>
    await axios.delete(
        `${API_ENDPOINTS.DATA.DB}`,
        { withCredentials: true },
    );

export async function uploadBackup(file: File): Promise<void> {
    const formData = new FormData();
    formData.append("dump_file", file);

    await axios.post(
        `${API_ENDPOINTS.DATA.DB}`,
        formData,
        {
            headers: { "Content-Type": "multipart/form-data" },
            withCredentials: true,
        },
    );
}
