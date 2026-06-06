import { Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Inventory from "./pages/Inventory";
import AddEditItem from "./pages/AddEditItem";
import Orders from "./pages/Orders";
import Transactions from "./pages/Transactions";
import PaymentPage from "./pages/PaymentPage";

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
            <Route path="/pay/:orderId" element={<PaymentPage />} />
        </Routes>
    );
}

export default App;
