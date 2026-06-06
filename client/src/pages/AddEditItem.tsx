import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Html5Qrcode } from "html5-qrcode";
import { Camera, Upload, X, ScanBarcode, Loader2 } from "lucide-react";
import { api } from "@/services/api";
import { playBeep } from "@/utils/beep";
import DashboardLayout from "@/components/DashboardLayout";

const UNIT_OPTIONS = [
    "piece", "kg", "g", "litre", "ml", "pack", "box", "dozen",
    "hour", "session", "job", "visit", "month", "day",
];

interface ProductData {
    name: string;
    barcode: string;
    mrp: string | null;
    hsn: { hsn: string; description: string; gst: number } | null;
    images: string[];
    attributes: Record<string, string>;
}

export default function AddEditItem() {
    const { itemId } = useParams<{ itemId: string }>();
    const navigate = useNavigate();
    const isEdit = Boolean(itemId);

    const [form, setForm] = useState({
        name: "",
        description: "",
        type: "product" as "product" | "service",
        ean: "",
        hsn: "",
        price: "",
        quantity: "",
        unit: "piece",
    });
    const [images, setImages] = useState<string[]>([]);
    const [uploading, setUploading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [scanMode, setScanMode] = useState(false);
    const [, setScanning] = useState(false);
    const [scanStatus, setScanStatus] = useState("");
    const [lookingUp, setLookingUp] = useState(false);
    const scannerRef = useRef<Html5Qrcode | null>(null);
    const lastCheckedRef = useRef<{ code: string; time: number }>({ code: "", time: 0 });
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (itemId) {
            fetchItem(itemId);
        }
    }, [itemId]);

    async function fetchItem(id: string) {
        try {
            const res = await api.get(`/api/inventory/${id}`);
            const item = res.data;
            setForm({
                name: item.name,
                description: item.description || "",
                type: item.type,
                ean: item.ean || "",
                hsn: item.hsn || "",
                price: item.price.toString(),
                quantity: item.quantity?.toString() || "",
                unit: item.unit,
            });
            setImages(item.images || []);
        } catch {
            navigate("/dashboard/inventory");
        }
    }

    // Barcode scanning
    const handleBarcodeScan = useCallback(async (decodedText: string) => {
        if (!/^\d{8,14}$/.test(decodedText)) return;
        const now = Date.now();
        const last = lastCheckedRef.current;
        if (last.code === decodedText && now - last.time < 5000) return;
        lastCheckedRef.current = { code: decodedText, time: now };

        playBeep();
        setScanStatus(`Found: ${decodedText}`);
        setForm((f) => ({ ...f, ean: decodedText }));
        stopScanner();
        setScanMode(false);

        // Auto-fill from barcode lookup
        setLookingUp(true);
        try {
            const { data } = await api.get<ProductData>(`/api/barcode/${decodedText}`);
            if (data) {
                setForm((f) => ({
                    ...f,
                    name: f.name || data.name || "",
                    price: f.price || data.mrp || "",
                    hsn: f.hsn || data.hsn?.hsn || "",
                    description: f.description || data.attributes?.Brand || "",
                }));
                if (data.images.length > 0) {
                    setImages((prev) => [...new Set([...prev, ...data.images])]);
                }
            }
        } catch {
            setScanStatus(`Barcode ${decodedText} set (product not found in database)`);
        } finally {
            setLookingUp(false);
        }
    }, []);

    async function startScanner() {
        setScanMode(true);
        setScanStatus("");
        // Wait for the DOM element to render before starting
        await new Promise((r) => setTimeout(r, 100));
        try {
            const scanner = new Html5Qrcode("item-barcode-reader");
            scannerRef.current = scanner;
            await scanner.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: { width: 280, height: 150 } },
                (decodedText) => handleBarcodeScan(decodedText),
                () => { }
            );
            setScanning(true);
        } catch (err) {
            setScanStatus(
                err instanceof Error
                    ? err.message
                    : "Camera access denied. Please allow camera permissions."
            );
            setScanMode(false);
        }
    }

    async function stopScanner() {
        if (scannerRef.current) {
            try {
                await scannerRef.current.stop();
                scannerRef.current.clear();
            } catch { }
            scannerRef.current = null;
            setScanning(false);
        }
    }

    // Manual barcode lookup
    async function lookupBarcode() {
        if (!form.ean || !/^\d{8,14}$/.test(form.ean)) return;
        setLookingUp(true);
        try {
            const { data } = await api.get<ProductData>(`/api/barcode/${form.ean}`);
            if (data) {
                setForm((f) => ({
                    ...f,
                    name: f.name || data.name || "",
                    price: f.price || data.mrp || "",
                    hsn: f.hsn || data.hsn?.hsn || "",
                    description: f.description || data.attributes?.Brand || "",
                }));
                if (data.images.length > 0) {
                    setImages((prev) => [...new Set([...prev, ...data.images])]);
                }
            }
        } catch {
            setScanStatus("Product not found for this barcode");
        } finally {
            setLookingUp(false);
        }
    }

    // Image handling
    async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
        const files = e.target.files;
        if (!files || files.length === 0) return;
        setUploading(true);

        for (const file of Array.from(files)) {
            const formData = new FormData();
            formData.append("file", file);
            try {
                const res = await api.post("/api/upload/image/", formData, {
                    headers: { "Content-Type": "multipart/form-data" },
                });
                setImages((prev) => [...prev, res.data.url]);
            } catch {
                console.error("Failed to upload image");
            }
        }
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
    }

    function removeImage(url: string) {
        setImages((prev) => prev.filter((img) => img !== url));
    }

    // Form submit
    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setSaving(true);

        const payload = {
            ...form,
            price: parseFloat(form.price),
            quantity: form.type === "product" ? parseInt(form.quantity) || 0 : null,
            ean: form.ean || null,
            hsn: form.hsn || null,
            description: form.description || null,
            images,
        };

        try {
            if (isEdit) {
                await api.patch(`/api/inventory/${itemId}`, payload);
            } else {
                await api.post("/api/inventory/", payload);
            }
            navigate("/dashboard/inventory");
        } catch (err) {
            console.error("Failed to save item", err);
        } finally {
            setSaving(false);
        }
    }

    return (
        <DashboardLayout>
            <div className="page-header">
                <h1>{isEdit ? "Edit Item" : "Add New Item"}</h1>
            </div>

            <form className="add-item-form" onSubmit={handleSubmit}>
                {/* Barcode Scanner Section */}
                {form.type === "product" && (
                    <section className="form-section neu-raised">
                        <h2 className="section-title">
                            <ScanBarcode size={18} /> Barcode
                        </h2>

                        <div className="barcode-row">
                            <input
                                className="neu-input"
                                value={form.ean}
                                onChange={(e) => setForm({ ...form, ean: e.target.value })}
                                placeholder="EAN / Barcode number"
                                inputMode="numeric"
                            />
                            <button
                                type="button"
                                className="neu-btn primary"
                                onClick={lookupBarcode}
                                disabled={lookingUp || !form.ean}
                            >
                                {lookingUp ? <Loader2 size={16} className="spin" /> : "Lookup"}
                            </button>
                            <button
                                type="button"
                                className="neu-btn"
                                onClick={scanMode ? () => { stopScanner(); setScanMode(false); } : startScanner}
                            >
                                <Camera size={16} /> {scanMode ? "Stop" : "Scan"}
                            </button>
                        </div>

                        {scanMode && (
                            <div id="item-barcode-reader" className="scanner-viewport" />
                        )}

                        {scanStatus && <p className="scan-status">{scanStatus}</p>}
                        {lookingUp && <p className="scan-status">Looking up product details...</p>}
                    </section>
                )}

                {/* Basic Details */}
                <section className="form-section neu-raised">
                    <h2 className="section-title">Details</h2>

                    <div className="form-row">
                        <label>Type</label>
                        <div className="toggle-group">
                            <button
                                type="button"
                                className={`neu-btn-sm ${form.type === "product" ? "active" : ""}`}
                                onClick={() => setForm({ ...form, type: "product" })}
                            >Product</button>
                            <button
                                type="button"
                                className={`neu-btn-sm ${form.type === "service" ? "active" : ""}`}
                                onClick={() => setForm({ ...form, type: "service" })}
                            >Service</button>
                        </div>
                    </div>

                    <div className="form-row">
                        <label>Name *</label>
                        <input
                            className="neu-input"
                            required
                            value={form.name}
                            onChange={(e) => setForm({ ...form, name: e.target.value })}
                            placeholder="Item name"
                        />
                    </div>

                    <div className="form-row">
                        <label>Description</label>
                        <input
                            className="neu-input"
                            value={form.description}
                            onChange={(e) => setForm({ ...form, description: e.target.value })}
                            placeholder="Optional description"
                        />
                    </div>

                    <div className="form-row-2col">
                        <div className="form-row">
                            <label>Price (₹) *</label>
                            <input
                                className="neu-input"
                                type="number"
                                step="0.01"
                                required
                                value={form.price}
                                onChange={(e) => setForm({ ...form, price: e.target.value })}
                                placeholder="0.00"
                            />
                        </div>
                        <div className="form-row">
                            <label>Unit</label>
                            <select
                                className="neu-input"
                                value={form.unit}
                                onChange={(e) => setForm({ ...form, unit: e.target.value })}
                            >
                                {UNIT_OPTIONS.map((u) => (
                                    <option key={u} value={u}>{u}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {form.type === "product" && (
                        <div className="form-row">
                            <label>Stock Quantity</label>
                            <input
                                className="neu-input"
                                type="number"
                                value={form.quantity}
                                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                                placeholder="0"
                            />
                        </div>
                    )}

                    <div className="form-row">
                        <label>HSN Code</label>
                        <input
                            className="neu-input"
                            value={form.hsn}
                            onChange={(e) => setForm({ ...form, hsn: e.target.value })}
                            placeholder="Optional"
                        />
                    </div>
                </section>

                {/* Images Section */}
                <section className="form-section neu-raised">
                    <h2 className="section-title">
                        <Camera size={18} /> Images
                    </h2>

                    {images.length > 0 && (
                        <div className="image-grid">
                            {images.map((url) => (
                                <div key={url} className="image-thumb">
                                    <img src={url} alt="Product" />
                                    <button
                                        type="button"
                                        className="image-remove"
                                        onClick={() => removeImage(url)}
                                        aria-label="Remove image"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="image-upload-row">
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/jpeg,image/png,image/webp,image/gif"
                            multiple
                            onChange={handleImageUpload}
                            className="file-input-hidden"
                            id="image-upload"
                        />
                        <label htmlFor="image-upload" className="neu-btn">
                            <Upload size={16} />
                            {uploading ? "Uploading..." : "Add Photos"}
                        </label>
                        <span className="upload-hint">JPEG, PNG, WebP • Max 5MB each</span>
                    </div>
                </section>

                {/* Actions */}
                <div className="form-actions">
                    <button type="button" className="neu-btn" onClick={() => navigate("/dashboard/inventory")}>
                        Cancel
                    </button>
                    <button type="submit" className="neu-btn primary" disabled={saving}>
                        {saving ? "Saving..." : isEdit ? "Update Item" : "Add to Inventory"}
                    </button>
                </div>
            </form>
        </DashboardLayout>
    );
}
