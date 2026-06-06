import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/services/api";

function ImageSlider({ images, alt }: { images: string[]; alt: string }) {
    const [current, setCurrent] = useState(0);

    if (images.length === 1) {
        return (
            <div className="product-images">
                <img src={images[0]} alt={alt} className="product-main-image" />
            </div>
        );
    }

    return (
        <div className="product-images">
            <div className="slider">
                <button
                    className="slider-btn slider-prev"
                    onClick={() => setCurrent((c) => (c - 1 + images.length) % images.length)}
                >
                    ‹
                </button>
                <img
                    src={images[current]}
                    alt={`${alt} ${current + 1}`}
                    className="product-main-image"
                />
                <button
                    className="slider-btn slider-next"
                    onClick={() => setCurrent((c) => (c + 1) % images.length)}
                >
                    ›
                </button>
            </div>
            <div className="slider-dots">
                {images.map((_, i) => (
                    <button
                        key={i}
                        className={`slider-dot ${i === current ? "active" : ""}`}
                        onClick={() => setCurrent(i)}
                    />
                ))}
            </div>
        </div>
    );
}

interface HsnData {
    hsn: string;
    description: string;
    gst: number;
}

interface ProductData {
    barcode: string;
    name: string;
    barcode_format: string;
    mrp: string | null;
    hsn: HsnData | null;
    images: string[];
    attributes: Record<string, string>;
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
                    <ImageSlider images={product.images} alt={product.name} />
                )}

                <h1 className="product-name">{product.name}</h1>

                {product.mrp && (
                    <div className="product-pricing">
                        <span className="price-label">MRP</span>
                        <span className="price-value">₹{product.mrp}</span>
                    </div>
                )}

                {product.hsn && (
                    <div className="product-hsn">
                        <div className="hsn-row">
                            <span className="hsn-label">HSN Code</span>
                            <span className="hsn-value">{product.hsn.hsn}</span>
                        </div>
                        <div className="hsn-row">
                            <span className="hsn-label">GST Rate</span>
                            <span className="hsn-gst">{product.hsn.gst}%</span>
                        </div>
                        <div className="hsn-desc">{product.hsn.description}</div>
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
            </div>
        </div>
    );
}
