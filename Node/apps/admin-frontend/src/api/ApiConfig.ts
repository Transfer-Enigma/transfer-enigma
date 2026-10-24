export const API_ENDPOINTS = {
    AUTH: {
        LOGIN: "/api/user/login",
        LOGOUT: "/api/user/logout",
        REFRESH: "/api/user/token/refresh",
        ME: "/api/user/me",
    },
    DATA: {
        UPDATE_FROM_GSHEETS: "/admin/api/data/update-from-gsheets",
        DB: "/admin/api/db/data",
    },
    DEMO_GUESTS: {
        ROOT: "/admin/api/demo-guests",
        byId: (id: number) => `/admin/api/demo-guests/${id}`,
    },
    SETTINGS: {
        ROOT: "/admin/api/db/settings",
        byId: (id: number) => `/admin/api/db/settings/${id}`,
    },
    CACHE_POLICIES: {
        ROOT: "/admin/api/cache/policies",
        byId: (id: number) => `/admin/api/cache/policies/${id}`,
        invalidate: () => "/admin/api/cache/policies/invalidate",
        invalidateSource: (source: string) =>
            `/admin/api/cache/policies/invalidate/${encodeURIComponent(source)}`,
    },
};
