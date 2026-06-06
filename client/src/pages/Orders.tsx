import { useState, useEffect } from "react";
import { ShoppingCart, Plus, Trash2 } from "lucide-react";
import { api } from "@/services/api";
import DashboardLayout from "@/components/DashboardLayout";

interface InventoryItem {
    id: string;
    name: string;
    price: number;
    quantity: number | null;
    unit: string;
    type: string;
}

interface OrderItem {
    inventory_item_id: string;
    quantity: number;
    name?: string;
    price?: number;
}

interface Order {
    id: string;
    customer_name: string | null;
    customer_phone: string | null;
    total_price: number;
    status: string;
    created_at: string;
    items: { id: string; inventory_item_id: string; quantity: number; price_at_purchase: number; item_name: string | null }[];
}

export default function Orders() {
    const [orders, setOrders] = useState<Order[]>([]);
    const [inventory, setInventory] = useState<InventoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [customerName, setCustomerName] = useState("");
    const [customerPhone, setCustomerPhone] = useState("");
    const [cart, setCart] = useState<OrderItem[]>([]);
    const [selectedItem, setSelectedItem] = useState("");
    const [qty, setQty] = useState("1");

    useEffect(() => {
        fetchOrders();
        fetchInventory();
    }, []);

    async function fetchOrders() {
        setLoading(true);
        try {
            const res = await api.get("/api/orders/");
            setOrders(res.data || []);
        } catch (err) {
            console.error("Failed to fetch orders", err);
        } finally {
            setLoading(false);
        }
    }

    async function fetchInventory() {
        try {
            const res = await api.get("/api/inventory/");
            setInventory(res.data || []);
        } catch (err) {
            console.error("Failed to fetch inventory", err);
        }
    }

    function addToCart() {
        if (!selectedItem) return;
        const inv = inventory.find((i) => i.id === selectedItem);
        if (!inv) return;
        const existing = cart.find((c) => c.inventory_item_id === selectedItem);
        if (existing) {
            setCart(cart.map((c) =>
                c.inventory_item_id === selectedItem
                    ? { ...c, quantity: c.quantity + parseInt(qty) }
                    : c
            ));
        } else {
            setCart([...cart, {
                inventory_item_id: selectedItem,
                quantity: parseInt(qty),
                name: inv.name,
                price: inv.price,
            }]);
        }
        setSelectedItem("");
        setQty("1");
    }

    function removeFromCart(itemId: string) {
        setCart(cart.filter((c) => c.inventory_item_id !== itemId));
    }

    async function placeOrder(e: React.FormEvent) {
        e.preventDefault();
        if (cart.length === 0) return;
        try {
            await api.post("/api/orders", {
                customer_name: customerName || null,
                customer_phone: customerPhone || null,
                items: cart.map(({ inventory_item_id, quantity }) => ({ inventory_item_id, quantity })),
            });
            setShowForm(false);
            setCart([]);
            setCustomerName("");
            setCustomerPhone("");
            fetchOrders();
        } catch (err) {
            console.error("Failed to create order", err);
        }
    }

    const cartTotal = cart.reduce((sum, c) => sum + (c.price || 0) * c.quantity, 0);

    return (
        <DashboardLayout>
            <div className="page-header">
                <h1>Orders</h1>
                <button className="neu-btn primary" onClick={() => setShowForm(true)}>
                    <Plus size={16} /> New Order
                </button>
            </div>

            {loading ? (
                <div className="loading-state">
                    <div className="spinner" />
                    <p>Loading orders...</p>
                </div>
            ) : orders.length === 0 ? (
                <div className="empty-state neu-raised">
                    <ShoppingCart size={48} strokeWidth={1} />
                    <p>No orders yet. Create your first order.</p>
                </div>
            ) : (
                <div className="orders-list">
                    {orders.map((order) => (
                        <div key={order.id} className="order-card neu-raised">
                            <div className="order-header">
                                <div>
                                    <span className={`status-badge ${order.status}`}>{order.status}</span>
                                    <span className="order-date">
                                        {new Date(order.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <span className="order-total">₹{order.total_price}</span>
                            </div>
                            {(order.customer_name || order.customer_phone) && (
                                <p className="order-customer">
                                    {order.customer_name} {order.customer_phone && `• ${order.customer_phone}`}
                                </p>
                            )}
                            <div className="order-items">
                                {order.items.map((oi) => (
                                    <span key={oi.id} className="order-item-chip">
                                        {oi.item_name || "Item"} × {oi.quantity}
                                    </span>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {showForm && (
                <div className="modal-overlay" onClick={() => setShowForm(false)}>
                    <div className="modal neu-raised" onClick={(e) => e.stopPropagation()}>
                        <h2>Create Order</h2>
                        <form onSubmit={placeOrder}>
                            <div className="form-row-2col">
                                <div className="form-row">
                                    <label>Customer Name</label>
                                    <input
                                        className="neu-input"
                                        value={customerName}
                                        onChange={(e) => setCustomerName(e.target.value)}
                                        placeholder="Optional"
                                    />
                                </div>
                                <div className="form-row">
                                    <label>Phone</label>
                                    <input
                                        className="neu-input"
                                        value={customerPhone}
                                        onChange={(e) => setCustomerPhone(e.target.value)}
                                        placeholder="Optional"
                                    />
                                </div>
                            </div>

                            <div className="cart-section">
                                <h3>Items</h3>
                                <div className="cart-add-row">
                                    <select
                                        className="neu-input"
                                        value={selectedItem}
                                        onChange={(e) => setSelectedItem(e.target.value)}
                                    >
                                        <option value="">Select item...</option>
                                        {inventory.map((inv) => (
                                            <option key={inv.id} value={inv.id}>
                                                {inv.name} — ₹{inv.price}/{inv.unit}
                                            </option>
                                        ))}
                                    </select>
                                    <input
                                        className="neu-input qty-input"
                                        type="number"
                                        min="1"
                                        value={qty}
                                        onChange={(e) => setQty(e.target.value)}
                                    />
                                    <button type="button" className="neu-btn-sm active" onClick={addToCart}>
                                        <Plus size={14} />
                                    </button>
                                </div>

                                {cart.length > 0 && (
                                    <div className="cart-items">
                                        {cart.map((c) => (
                                            <div key={c.inventory_item_id} className="cart-item">
                                                <span>{c.name} × {c.quantity}</span>
                                                <span>₹{((c.price || 0) * c.quantity).toFixed(2)}</span>
                                                <button
                                                    type="button"
                                                    className="icon-btn danger"
                                                    onClick={() => removeFromCart(c.inventory_item_id)}
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        ))}
                                        <div className="cart-total">
                                            <strong>Total: ₹{cartTotal.toFixed(2)}</strong>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="form-actions">
                                <button type="button" className="neu-btn" onClick={() => setShowForm(false)}>Cancel</button>
                                <button type="submit" className="neu-btn primary" disabled={cart.length === 0}>
                                    Place Order
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </DashboardLayout>
    );
}
