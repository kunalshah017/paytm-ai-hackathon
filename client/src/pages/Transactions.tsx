import { useState, useEffect } from "react";
import { CreditCard } from "lucide-react";
import { api } from "@/services/api";
import DashboardLayout from "@/components/DashboardLayout";

interface Transaction {
    id: string;
    created_at: string;
    order_id: string;
    payment_link: string | null;
    amount: number;
    payment_method: string | null;
    status: string;
}

export default function Transactions() {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("");

    useEffect(() => {
        fetchTransactions();
    }, [filter]);

    async function fetchTransactions() {
        setLoading(true);
        try {
            const params = filter ? `?status=${filter}` : "";
            const res = await api.get(`/api/transactions/${params}`);
            setTransactions(res.data || []);
        } catch (err) {
            console.error("Failed to fetch transactions", err);
        } finally {
            setLoading(false);
        }
    }

    async function updateStatus(id: string, status: string) {
        try {
            await api.patch(`/api/transactions/${id}`, { status });
            fetchTransactions();
        } catch (err) {
            console.error("Failed to update transaction", err);
        }
    }

    return (
        <DashboardLayout>
            <div className="page-header">
                <h1>Transactions</h1>
            </div>

            <div className="toolbar">
                <div className="filter-group">
                    <button className={`neu-btn-sm ${filter === "" ? "active" : ""}`} onClick={() => setFilter("")}>All</button>
                    <button className={`neu-btn-sm ${filter === "pending" ? "active" : ""}`} onClick={() => setFilter("pending")}>Pending</button>
                    <button className={`neu-btn-sm ${filter === "paid" ? "active" : ""}`} onClick={() => setFilter("paid")}>Paid</button>
                    <button className={`neu-btn-sm ${filter === "cancelled" ? "active" : ""}`} onClick={() => setFilter("cancelled")}>Cancelled</button>
                </div>
            </div>

            {loading ? (
                <div className="loading-state">
                    <div className="spinner" />
                    <p>Loading transactions...</p>
                </div>
            ) : transactions.length === 0 ? (
                <div className="empty-state neu-raised">
                    <CreditCard size={48} strokeWidth={1} />
                    <p>No transactions yet.</p>
                </div>
            ) : (
                <div className="transactions-list">
                    {transactions.map((txn) => (
                        <div key={txn.id} className="txn-card neu-raised">
                            <div className="txn-header">
                                <span className={`status-badge ${txn.status}`}>{txn.status}</span>
                                <span className="txn-date">{new Date(txn.created_at).toLocaleDateString()}</span>
                            </div>
                            <div className="txn-body">
                                <span className="txn-amount">₹{txn.amount}</span>
                                {txn.payment_method && <span className="txn-method">{txn.payment_method}</span>}
                            </div>
                            {txn.status === "pending" && (
                                <div className="txn-actions">
                                    <button className="neu-btn-sm active" onClick={() => updateStatus(txn.id, "paid")}>
                                        Mark Paid
                                    </button>
                                    <button className="neu-btn-sm danger" onClick={() => updateStatus(txn.id, "cancelled")}>
                                        Cancel
                                    </button>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </DashboardLayout>
    );
}
