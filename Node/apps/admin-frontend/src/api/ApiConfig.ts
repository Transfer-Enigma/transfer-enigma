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
    RATES: {
        ROOT: "/admin/api/db/rates",
        byId: (id: number) => `/admin/api/db/rates/${id}`,
    },
};
