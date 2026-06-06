import { useState, useEffect } from "react";
import { Package, ShoppingCart, CreditCard, TrendingUp } from "lucide-react";
import { api } from "@/services/api";
import DashboardLayout from "@/components/DashboardLayout";

interface Stats {
    totalItems: number;
    totalOrders: number;
    totalRevenue: number;
    pendingPayments: number;
}

export default function Dashboard() {
    const [stats, setStats] = useState<Stats>({
        totalItems: 0,
        totalOrders: 0,
        totalRevenue: 0,
        pendingPayments: 0,
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStats();
    }, []);

    async function fetchStats() {
        setLoading(true);
        try {
            const [invRes, ordRes, txnRes] = await Promise.all([
                api.get("/api/inventory/"),
                api.get("/api/orders/"),
                api.get("/api/transactions/"),
            ]);
            const orders = ordRes.data || [];
            const txns = txnRes.data || [];
            setStats({
                totalItems: (invRes.data || []).length,
                totalOrders: orders.length,
                totalRevenue: orders.reduce((s: number, o: { total_price: number }) => s + o.total_price, 0),
                pendingPayments: txns.filter((t: { status: string }) => t.status === "pending").length,
            });
        } catch (err) {
            console.error("Failed to fetch stats", err);
        } finally {
            setLoading(false);
        }
    }

    const cards = [
        { label: "Inventory Items", value: stats.totalItems, icon: Package, color: "var(--primary)" },
        { label: "Total Orders", value: stats.totalOrders, icon: ShoppingCart, color: "#00A63D" },
        { label: "Revenue", value: `₹${stats.totalRevenue.toFixed(0)}`, icon: TrendingUp, color: "#006666" },
        { label: "Pending Payments", value: stats.pendingPayments, icon: CreditCard, color: "#FE9900" },
    ];

    return (
        <DashboardLayout>
            <div className="page-header">
                <h1>Dashboard</h1>
            </div>

            {loading ? (
                <div className="loading-state">
                    <div className="spinner" />
                </div>
            ) : (
                <div className="stats-grid">
                    {cards.map((card) => {
                        const Icon = card.icon;
                        return (
                            <div key={card.label} className="stat-card neu-raised">
                                <div className="stat-icon" style={{ color: card.color }}>
                                    <Icon size={28} />
                                </div>
                                <div className="stat-content">
                                    <span className="stat-value">{card.value}</span>
                                    <span className="stat-label">{card.label}</span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </DashboardLayout>
    );
}
