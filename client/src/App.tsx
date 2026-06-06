import { Routes, Route } from "react-router-dom";
import Scan from "./pages/Scan";
import ProductDetails from "./pages/ProductDetails";

function App() {
    return (
        <Routes>
            <Route path="/" element={<Scan />} />
            <Route path="/scan" element={<Scan />} />
            <Route path="/product/:barcode" element={<ProductDetails />} />
        </Routes>
    );
}

export default App;
