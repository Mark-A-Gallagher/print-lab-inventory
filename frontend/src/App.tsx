// App.tsx

import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";

import Dashboard from "./pages/Dashboard";
import Inventory from "./pages/Inventory";
import Machines from "./pages/Machines";
import PrintRequests from "./pages/PrintRequests";
import SpoolDetail from "./pages/SpoolDetail";

export default function App() {
    return (
        <Routes>
            <Route element={<Layout />}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/inventory" element={<Inventory />} />
                <Route path="/machines" element={<Machines />} />
                <Route path="/requests" element={<PrintRequests />} />
                <Route path="/spools/:id" element={<SpoolDetail />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}