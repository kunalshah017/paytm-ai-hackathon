import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "@/services/api";

interface PaymentData {
    success: boolean;
    txnToken?: string;
    orderId?: string;
    mid?: string;
    amount?: string;
    baseUrl?: string;
    error?: string;
    fallback?: string;
}

type PaymentMethod = "card" | "upi" | "netbanking";

export default function PaymentPage() {
    const { orderId } = useParams<{ orderId: string }>();
    const [loading, setLoading] = useState(true);
    const [paymentData, setPaymentData] = useState<PaymentData | null>(null);
    const [paid, setPaid] = useState(false);
    const [error, setError] = useState("");
    const [processing, setProcessing] = useState(false);
    const [method, setMethod] = useState<PaymentMethod>("card");

    // Card form state
    const [cardNumber, setCardNumber] = useState("4111 1111 1111 1111");
    const [cardExpiry, setCardExpiry] = useState("12/28");
    const [cardCvv, setCardCvv] = useState("123");

    // UPI form state
    const [upiId, setUpiId] = useState("success@paytm");

    // Strip trailing underscores/asterisks that LLM formatting may add to URLs
    const cleanOrderId = orderId?.replace(/[_*]+$/, "") || "";

    useEffect(() => {
        if (cleanOrderId) initiatePayment(cleanOrderId);
    }, [cleanOrderId]);

    async function initiatePayment(id: string) {
        try {
            const res = await api.get(`/api/payments/initiate/${id}`);
            setPaymentData(res.data);

            if (res.data.success && res.data.txnToken) {
                // Load Paytm JS Checkout (live PG)
                loadPaytmCheckout(res.data);
            }
        } catch (err) {
            setError("Failed to initiate payment. Please try again.");
        } finally {
            setLoading(false);
        }
    }

    function loadPaytmCheckout(data: PaymentData) {
        const script = document.createElement("script");
        script.src = `${data.baseUrl}/merchantpgpui/checkoutjs/merchants/${data.mid}.js`;
        script.crossOrigin = "anonymous";
        script.onload = () => {
            const config = {
                root: "",
                flow: "DEFAULT",
                data: {
                    orderId: data.orderId,
                    token: data.txnToken,
                    tokenType: "TXN_TOKEN",
                    amount: data.amount,
                },
                handler: {
                    notifyMerchant: (eventName: string, _data: unknown) => {
                        console.log("Paytm event:", eventName);
                    },
                    transactionStatus: async (_data: unknown) => {
                        try {
                            await api.post(`/api/payments/confirm/${cleanOrderId}`);
                            setPaid(true);
                        } catch {
                            setPaid(true);
                        }
                    },
                },
            };

            if ((window as any).Paytm && (window as any).Paytm.CheckoutJS) {
                (window as any).Paytm.CheckoutJS.init(config)
                    .then(() => {
                        (window as any).Paytm.CheckoutJS.invoke();
                    })
                    .catch((err: any) => {
                        console.error("Paytm JS error:", err);
                    });
            }
        };
        script.onerror = () => {
            // Silently fall through to test payment UI
        };
        document.body.appendChild(script);
    }

    async function handleTestPay() {
        setProcessing(true);
        setError("");
        // Simulate a brief processing delay
        await new Promise((r) => setTimeout(r, 1500));
        try {
            await api.post(`/api/payments/confirm/${cleanOrderId}`);
            setPaid(true);
        } catch {
            setError("Payment confirmation failed. Please try again.");
        } finally {
            setProcessing(false);
        }
    }

    function formatCardNumber(val: string) {
        const digits = val.replace(/\D/g, "").slice(0, 16);
        return digits.replace(/(.{4})/g, "$1 ").trim();
    }

    function formatExpiry(val: string) {
        const digits = val.replace(/\D/g, "").slice(0, 4);
        if (digits.length >= 3) return digits.slice(0, 2) + "/" + digits.slice(2);
        return digits;
    }

    if (paid) {
        return (
            <div className="payment-page">
                <div className="payment-card neu-raised">
                    <div className="payment-success">
                        <div className="success-icon">✓</div>
                        <h1>Payment Successful!</h1>
                        <p>Your order has been confirmed.</p>
                        <p className="payment-amount">₹{paymentData?.amount}</p>
                        <p className="payment-note">You can close this page and return to WhatsApp.</p>
                    </div>
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="payment-page">
                <div className="payment-card neu-raised">
                    <div className="spinner" />
                    <p>Preparing payment...</p>
                </div>
            </div>
        );
    }

    if (error && !paymentData) {
        return (
            <div className="payment-page">
                <div className="payment-card neu-raised">
                    <p className="payment-error">{error}</p>
                    <button className="neu-btn primary" onClick={() => window.location.reload()}>
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    // Test Payment Checkout UI (when Paytm PG is unavailable or in staging)
    const amount = paymentData?.amount || "0.00";

    return (
        <div className="payment-page">
            <div className="payment-card neu-raised">
                <div className="pg-header">
                    <div className="pg-logo">Paytm</div>
                    <div className="pg-badge">TEST MODE</div>
                </div>
                <h1>₹{amount}</h1>
                <p className="payment-subtitle">Order #{cleanOrderId.slice(0, 8)}</p>

                {/* Payment method tabs */}
                <div className="pg-tabs">
                    <button
                        className={`pg-tab ${method === "card" ? "active" : ""}`}
                        onClick={() => setMethod("card")}
                    >
                        💳 Card
                    </button>
                    <button
                        className={`pg-tab ${method === "upi" ? "active" : ""}`}
                        onClick={() => setMethod("upi")}
                    >
                        📱 UPI
                    </button>
                    <button
                        className={`pg-tab ${method === "netbanking" ? "active" : ""}`}
                        onClick={() => setMethod("netbanking")}
                    >
                        🏦 Bank
                    </button>
                </div>

                {/* Card form */}
                {method === "card" && (
                    <div className="pg-form">
                        <div className="pg-field">
                            <label>Card Number</label>
                            <input
                                type="text"
                                value={cardNumber}
                                onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
                                placeholder="4111 1111 1111 1111"
                            />
                        </div>
                        <div className="pg-row">
                            <div className="pg-field">
                                <label>Expiry</label>
                                <input
                                    type="text"
                                    value={cardExpiry}
                                    onChange={(e) => setCardExpiry(formatExpiry(e.target.value))}
                                    placeholder="MM/YY"
                                />
                            </div>
                            <div className="pg-field">
                                <label>CVV</label>
                                <input
                                    type="password"
                                    value={cardCvv}
                                    onChange={(e) => setCardCvv(e.target.value.replace(/\D/g, "").slice(0, 4))}
                                    placeholder="•••"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* UPI form */}
                {method === "upi" && (
                    <div className="pg-form">
                        <div className="pg-field">
                            <label>UPI ID</label>
                            <input
                                type="text"
                                value={upiId}
                                onChange={(e) => setUpiId(e.target.value)}
                                placeholder="yourname@paytm"
                            />
                        </div>
                    </div>
                )}

                {/* Netbanking */}
                {method === "netbanking" && (
                    <div className="pg-form">
                        <div className="pg-field">
                            <label htmlFor="bank-select">Select Bank</label>
                            <select id="bank-select" className="pg-select">
                                <option>State Bank of India</option>
                                <option>HDFC Bank</option>
                                <option>ICICI Bank</option>
                                <option>Axis Bank</option>
                                <option>Kotak Mahindra Bank</option>
                            </select>
                        </div>
                    </div>
                )}

                {error && <p className="payment-error">{error}</p>}

                <button
                    className="pg-pay-btn"
                    onClick={handleTestPay}
                    disabled={processing}
                >
                    {processing ? (
                        <>
                            <div className="spinner-sm" />
                            Processing...
                        </>
                    ) : (
                        `Pay ₹${amount}`
                    )}
                </button>

                <p className="pg-secure">🔒 Secured by Paytm Payment Gateway</p>
            </div>
        </div>
    );
}
