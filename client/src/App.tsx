import { Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Inventory from "./pages/Inventory";
import AddEditItem from "./pages/AddEditItem";
import Orders from "./pages/Orders";
import Transactions from "./pages/Transactions";

function App() {
    return (
        <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/dashboard/inventory" element={<Inventory />} />
            <Route path="/dashboard/inventory/add" element={<AddEditItem />} />
            <Route path="/dashboard/inventory/edit/:itemId" element={<AddEditItem />} />
            <Route path="/dashboard/orders" element={<Orders />} />
            <Route path="/dashboard/transactions" element={<Transactions />} />
        </Routes>
    );
}

export default App;
