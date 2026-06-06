import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Package, ShoppingCart, CreditCard, BarChart3, Menu, X, ScanBarcode } from "lucide-react";

interface DashboardLayoutProps {
    children: React.ReactNode;
}

const navItems = [
    { path: "/dashboard", label: "Overview", icon: BarChart3 },
    { path: "/dashboard/inventory", label: "Inventory", icon: Package },
    { path: "/dashboard/orders", label: "Orders", icon: ShoppingCart },
    { path: "/dashboard/transactions", label: "Transactions", icon: CreditCard },
];

export default function DashboardLayout({ children }: DashboardLayoutProps) {
    const location = useLocation();
    const [sidebarOpen, setSidebarOpen] = useState(false);

    return (
        <div className="dashboard-layout">
            <button
                className="sidebar-toggle"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                aria-label="Toggle menu"
            >
                {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>

            <aside className={`dashboard-sidebar ${sidebarOpen ? "open" : ""}`}>
                <div className="sidebar-brand">
                    <span className="brand-icon">₹</span>
                    <span className="brand-text">Merchant Dashboard</span>
                </div>
                <nav className="sidebar-nav">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={`sidebar-link ${isActive ? "active" : ""}`}
                                onClick={() => setSidebarOpen(false)}
                            >
                                <Icon size={18} />
                                <span>{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>
                <div className="sidebar-footer">
                    <Link to="/dashboard/inventory/add" className="sidebar-link" onClick={() => setSidebarOpen(false)}>
                        <ScanBarcode size={18} />
                        <span>Scan & Add Product</span>
                    </Link>
                </div>
            </aside>

            <main className="dashboard-main">
                {children}
            </main>
        </div>
    );
}
