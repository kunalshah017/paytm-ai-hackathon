import { useEffect, useState } from "react";
import { api } from "../services/api";

function Home() {
    const [message, setMessage] = useState("");

    useEffect(() => {
        api
            .get<{ message: string }>("/api/")
            .then((res) => setMessage(res.data.message))
            .catch((err) => console.error(err));
    }, []);

    return (
        <div style={{ padding: "2rem", textAlign: "center" }}>
            <h1>Paytm AI Hackathon</h1>
            <p>{message || "Loading..."}</p>
        </div>
    );
}

export default Home;
