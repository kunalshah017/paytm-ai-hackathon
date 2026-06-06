import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/services/api";

interface ProductData {
    barcode: string;
    name: string;
    barcode_format: string;
    mrp: string | null;
    images: string[];
    attributes: Record<string, string>;
    stores: { name: string; price?: string; url: string }[];
}

export default function ProductDetails() {
    const { barcode } = useParams<{ barcode: string }>();
    const navigate = useNavigate();
    const [product, setProduct] = useState<ProductData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!barcode) return;
        fetchProduct(barcode);
    }, [barcode]);

    async function fetchProduct(code: string) {
        setLoading(true);
        setError("");
        try {
            const { data } = await api.get<ProductData>(`/api/barcode/${code}`);
            setProduct(data);
        } catch (err: unknown) {
            if (err && typeof err === "object" && "response" in err) {
                const axiosErr = err as { response?: { status: number } };
                if (axiosErr.response?.status === 404) {
                    setError("Product not found for this barcode.");
                } else {
                    setError("Failed to fetch product details.");
                }
            } else {
                setError("Network error. Please try again.");
            }
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return (
            <div className="product-page">
                <div className="product-loading">
                    <div className="spinner" />
                    <p>Looking up barcode {barcode}...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="product-page">
                <div className="product-error">
                    <p>{error}</p>
                    <button onClick={() => navigate("/scan")}>
                        Scan Again
                    </button>
                </div>
            </div>
        );
    }

    if (!product) return null;

    return (
        <div className="product-page">
            <button className="back-btn" onClick={() => navigate("/scan")}>
                ← Scan Another
            </button>

            <div className="product-card">
                {product.images.length > 0 && (
                    <div className="product-images">
                        <img
                            src={product.images[0]}
                            alt={product.name}
                            className="product-main-image"
                        />
                    </div>
                )}

                <h1 className="product-name">{product.name}</h1>

                {product.mrp && (
                    <div className="product-pricing">
                        <span className="price-label">MRP</span>
                        <span className="price-value">₹{product.mrp}</span>
                    </div>
                )}

                <div className="product-barcode-info">
                    <span className="barcode-label">Barcode:</span>
                    <span className="barcode-value">{product.barcode}</span>
                    {product.barcode_format && (
                        <span className="barcode-format">
                            ({product.barcode_format})
                        </span>
                    )}
                </div>

                {Object.keys(product.attributes).length > 0 && (
                    <div className="product-attributes">
                        <h2>Product Details</h2>
                        <dl>
                            {Object.entries(product.attributes).map(
                                ([key, value]) => (
                                    <div key={key} className="attr-row">
                                        <dt>{key}</dt>
                                        <dd>{value}</dd>
                                    </div>
                                )
                            )}
                        </dl>
                    </div>
                )}

                {product.stores.length > 0 && (
                    <div className="product-stores">
                        <h2>Available At</h2>
                        <ul>
                            {product.stores.map((store, i) => (
                                <li key={i}>
                                    <a
                                        href={store.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        {store.name}
                                        {store.price && (
                                            <span className="store-price">
                                                {store.price}
                                            </span>
                                        )}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
}
