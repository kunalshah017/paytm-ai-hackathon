import { useEffect, useRef, useState, useCallback } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { useNavigate } from "react-router-dom";
import { api } from "@/services/api";

export default function BarcodeScanner() {
    const scannerRef = useRef<Html5Qrcode | null>(null);
    const [error, setError] = useState<string>("");
    const [scanning, setScanning] = useState(false);
    const [checking, setChecking] = useState<string>("");
    const [notFound, setNotFound] = useState<string>("");
    const navigate = useNavigate();

    // Debounce: track last checked barcode and timestamp
    const lastCheckedRef = useRef<{ code: string; time: number }>({ code: "", time: 0 });
    const checkingRef = useRef(false);

    useEffect(() => {
        startScanner();
        return () => {
            stopScanner();
        };
    }, []);

    const handleBarcodeScan = useCallback(async (decodedText: string) => {
        if (!/^\d{8,14}$/.test(decodedText)) return;

        // Debounce: don't re-check the same code within 5 seconds
        const now = Date.now();
        const last = lastCheckedRef.current;
        if (last.code === decodedText && now - last.time < 5000) return;

        // Don't start a new check if one is in progress
        if (checkingRef.current) return;

        lastCheckedRef.current = { code: decodedText, time: now };
        checkingRef.current = true;
        setChecking(decodedText);
        setNotFound("");

        try {
            const { data } = await api.get(`/api/barcode/${decodedText}`);
            if (data && data.name) {
                // Product found — navigate
                stopScanner();
                navigate(`/product/${decodedText}`);
            }
        } catch {
            // Product not found — keep scanning
            setNotFound(decodedText);
            setTimeout(() => setNotFound(""), 3000);
        } finally {
            checkingRef.current = false;
            setChecking("");
        }
    }, [navigate]);

    async function startScanner() {
        try {
            const scanner = new Html5Qrcode("barcode-reader");
            scannerRef.current = scanner;

            await scanner.start(
                { facingMode: "environment" },
                {
                    fps: 10,
                    qrbox: { width: 280, height: 150 },
                },
                (decodedText) => {
                    handleBarcodeScan(decodedText);
                },
                () => {
                    // ignore scan failures (no barcode in frame)
                }
            );
            setScanning(true);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Camera access denied. Please allow camera permissions."
            );
        }
    }

    async function stopScanner() {
        if (scannerRef.current) {
            try {
                await scannerRef.current.stop();
                scannerRef.current.clear();
            } catch {
                // ignore cleanup errors
            }
            scannerRef.current = null;
            setScanning(false);
        }
    }

    return (
        <div className="scanner-page">
            <h1>Scan Barcode</h1>
            <p className="scanner-hint">
                Point your camera at a product barcode
            </p>

            <div id="barcode-reader" className="scanner-viewport" />

            {error && (
                <div className="scanner-error">
                    <p>{error}</p>
                    <button onClick={() => { setError(""); startScanner(); }}>
                        Retry
                    </button>
                </div>
            )}

            {checking && (
                <p className="scanner-status">Looking up {checking}...</p>
            )}

            {notFound && (
                <p className="scanner-not-found">Product not found for {notFound}, keep scanning...</p>
            )}

            {scanning && !checking && !notFound && (
                <p className="scanner-status">Scanning...</p>
            )}

            <ManualEntry />
        </div>
    );
}

function ManualEntry() {
    const [barcode, setBarcode] = useState("");
    const navigate = useNavigate();

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        const trimmed = barcode.trim();
        if (/^\d{8,14}$/.test(trimmed)) {
            navigate(`/product/${trimmed}`);
        }
    }

    return (
        <form className="manual-entry" onSubmit={handleSubmit}>
            <p>Or enter barcode manually:</p>
            <div className="manual-entry-row">
                <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    placeholder="Enter barcode number"
                    value={barcode}
                    onChange={(e) => setBarcode(e.target.value)}
                />
                <button type="submit">Lookup</button>
            </div>
        </form>
    );
}
