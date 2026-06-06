import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { useNavigate } from "react-router-dom";

export default function BarcodeScanner() {
    const scannerRef = useRef<Html5Qrcode | null>(null);
    const [error, setError] = useState<string>("");
    const [scanning, setScanning] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        startScanner();
        return () => {
            stopScanner();
        };
    }, []);

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
                    // Only navigate for numeric barcodes
                    if (/^\d{8,14}$/.test(decodedText)) {
                        stopScanner();
                        navigate(`/product/${decodedText}`);
                    }
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

            {scanning && (
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
