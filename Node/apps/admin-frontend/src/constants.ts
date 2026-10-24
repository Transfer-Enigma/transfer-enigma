export const ROUTES = {
    ROOT: import.meta.env.VITE_PUBLIC_URL || "/",
    LOGIN: `${import.meta.env.VITE_PUBLIC_URL || ""}/login`,
    DASHBOARD: `${import.meta.env.VITE_PUBLIC_URL || ""}/dashboard`,
    ROUTES_MANAGEMENT: `${import.meta.env.VITE_PUBLIC_URL || ""}/routes-management`,
    POINTS_MANAGEMENT: `${import.meta.env.VITE_PUBLIC_URL || ""}/points-management`,
    DATA_IMPORT: `${import.meta.env.VITE_PUBLIC_URL || ""}/data-import`,
    DEMO_GUESTS: `${import.meta.env.VITE_PUBLIC_URL || ""}/demo-guests`,
    SETTINGS: `${import.meta.env.VITE_PUBLIC_URL || ""}/settings`,
    CACHE: `${import.meta.env.VITE_PUBLIC_URL || ""}/cache`,
    MAIN_SITE: import.meta.env.VITE_REACT_ROUTING_MAIN_SITE || "/",
};
