export const API_ENDPOINTS = {
    AUTH: {
        LOGIN: "/api/user/login",
        LOGOUT: "/api/user/logout",
        REFRESH: "/api/user/token/refresh",
        ME: "/api/user/me",
    },
    DATA: {
        UPDATE_FROM_GSHEETS: "/admin/api/data/update-from-gsheets",
        VALIDATE_FROM_GSHEETS: "/admin/api/data/validate-from-gsheets",
        DB: "/admin/api/db/data",
    },
    SYNC_DOCUMENTS: {
        ROOT: "/admin/api/db/sync-documents",
        byId: (id: number) => `/admin/api/db/sync-documents/${id}`,
        SHEETS_PREVIEW: "/admin/api/db/sync-documents/sheets-preview",
    },
    DEMO_GUESTS: {
        ROOT: "/admin/api/demo-guests",
        byId: (id: number) => `/admin/api/demo-guests/${id}`,
    },
    SETTINGS: {
        ROOT: "/admin/api/db/settings",
        byId: (id: number) => `/admin/api/db/settings/${id}`,
    },
};
