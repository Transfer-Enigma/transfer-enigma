import { createBrowserRouter } from "react-router-dom";
import { ROUTES } from "./constants";
import MainLayout from "@/layouts/MainLayout";
import Dashboard from "@/pages/Dashboard";
import DataImport from "@/pages/DataImport";
import DemoGuests from "@/pages/DemoGuests";
import RatesManagement from "@/pages/RatesManagement";
import RequireAuth from "@/providers/RequireAuth";
import EmptyLayout from "@/layouts/EmptyLayout";
import Login from "@/pages/Login";


export const routesConfig = [
    {
        element: <EmptyLayout />,
        children: [
            { path: ROUTES.LOGIN, element: <Login /> },
        ],
    },
    {
        element: <RequireAuth fallbackURL={ ROUTES.LOGIN }><MainLayout /></RequireAuth>,
        children: [
            { path: ROUTES.ROOT, element: <Dashboard /> },
            { path: ROUTES.DASHBOARD, element: <Dashboard /> },
            { path: ROUTES.DATA_IMPORT, element: <DataImport /> },
            { path: ROUTES.DEMO_GUESTS, element: <DemoGuests /> },
            { path: ROUTES.RATES_MANAGEMENT, element: <RatesManagement /> },
        ],
    },
];

export default createBrowserRouter(routesConfig);
