import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Search, Pencil, Trash2, Package, Wrench } from "lucide-react";
import { api } from "@/services/api";
import DashboardLayout from "@/components/DashboardLayout";

interface InventoryItem {
    id: string;
    name: string;
    description: string | null;
    type: "product" | "service";
    ean: string | null;
    hsn: string | null;
    price: number;
    quantity: number | null;
    unit: string;
    images: string[];
    created_at: string;
    updated_at: string;
}

export default function Inventory() {
    const navigate = useNavigate();
    const [items, setItems] = useState<InventoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [filterType, setFilterType] = useState<string>("");

    useEffect(() => {
        fetchItems();
    }, [filterType]);

    async function fetchItems() {
        setLoading(true);
        try {
            const params = filterType ? `?type=${filterType}` : "";
            const res = await api.get(`/api/inventory/${params}`);
            setItems(res.data || []);
        } catch (err) {
            console.error("Failed to fetch inventory", err);
        } finally {
            setLoading(false);
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Delete this item?")) return;
        try {
            await api.delete(`/api/inventory/${id}`);
            fetchItems();
        } catch (err) {
            console.error("Failed to delete item", err);
        }
    }

    const filtered = items.filter(
        (i) => i.name.toLowerCase().includes(search.toLowerCase()) ||
            (i.ean && i.ean.includes(search))
    );

    return (
        <DashboardLayout>
            <div className="page-header">
                <h1>Inventory</h1>
                <button className="neu-btn primary" onClick={() => navigate("/dashboard/inventory/add")}>
                    <Plus size={16} /> Add Item
                </button>
            </div>

            <div className="toolbar">
                <div className="search-box neu-inset">
                    <Search size={16} />
                    <input
                        type="text"
                        placeholder="Search by name or EAN..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <div className="filter-group">
                    <button
                        className={`neu-btn-sm ${filterType === "" ? "active" : ""}`}
                        onClick={() => setFilterType("")}
                    >All</button>
                    <button
                        className={`neu-btn-sm ${filterType === "product" ? "active" : ""}`}
                        onClick={() => setFilterType("product")}
                    ><Package size={14} /> Products</button>
                    <button
                        className={`neu-btn-sm ${filterType === "service" ? "active" : ""}`}
                        onClick={() => setFilterType("service")}
                    ><Wrench size={14} /> Services</button>
                </div>
            </div>

            {loading ? (
                <div className="loading-state">
                    <div className="spinner" />
                    <p>Loading inventory...</p>
                </div>
            ) : filtered.length === 0 ? (
                <div className="empty-state neu-raised">
                    <Package size={48} strokeWidth={1} />
                    <p>No items found. Add your first product or service.</p>
                </div>
            ) : (
                <div className="inventory-grid">
                    {filtered.map((item) => (
                        <div key={item.id} className="inventory-card neu-raised">
                            {item.images && item.images.length > 0 && (
                                <div className="card-image">
                                    <img src={item.images[0]} alt={item.name} />
                                </div>
                            )}
                            <div className="card-header">
                                <span className={`type-badge ${item.type}`}>
                                    {item.type === "product" ? <Package size={12} /> : <Wrench size={12} />}
                                    {item.type}
                                </span>
                                <div className="card-actions">
                                    <button className="icon-btn" onClick={() => navigate(`/dashboard/inventory/edit/${item.id}`)} aria-label="Edit">
                                        <Pencil size={14} />
                                    </button>
                                    <button className="icon-btn danger" onClick={() => handleDelete(item.id)} aria-label="Delete">
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>
                            <h3 className="card-title">{item.name}</h3>
                            {item.description && <p className="card-desc">{item.description}</p>}
                            <div className="card-meta">
                                <span className="price">₹{item.price}</span>
                                <span className="unit">/{item.unit}</span>
                            </div>
                            <div className="card-footer">
                                {item.type === "product" && (
                                    <span className={`stock ${(item.quantity ?? 0) <= 5 ? "low" : ""}`}>
                                        Stock: {item.quantity ?? 0}
                                    </span>
                                )}
                                {item.ean && <span className="ean">EAN: {item.ean}</span>}
                                {item.hsn && <span className="hsn">HSN: {item.hsn}</span>}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </DashboardLayout>
    );
}
