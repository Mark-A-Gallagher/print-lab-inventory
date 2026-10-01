import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import SpoolCard from "../components/SpoolCard";
import Modal from "../components/Modal";
import SpoolForm from "../components/SpoolForm";
import type { Spool } from "../types";
import "./Inventory.css";

export default function Inventory() {
    const navigate = useNavigate();
    const [spools, setSpools] = useState<Spool[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [showSpoolForm, setShowSpoolForm] = useState(false);

    useEffect(() => {
        loadSpools();
    }, []);

    const loadSpools = async () => {
        try {
            setError(null);
            setLoading(true);
            const data = await api.getSpools();
            setSpools(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load spools");
        } finally {
            setLoading(false);
        }
    };

    const filteredSpools = spools.filter((spool) =>
        spool.id.toString().includes(searchTerm)
    );

    if (loading) return <div className="loading">Loading inventory...</div>;
    if (error) return <div className="error">Error: {error}</div>;

    return (
        <>
            <div className="inventory">
                <div className="inventory-header">
                    <h1>Filament Inventory</h1>
                    <button
                        className="btn-primary"
                        onClick={() => setShowSpoolForm(true)}
                    >
                        + Add Spool
                    </button>
                </div>

                <div className="search-box">
                    <input
                        type="text"
                        placeholder="Search by spool ID..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                {filteredSpools.length === 0 ? (
                    <div className="empty-state">
                        {searchTerm
                            ? "No spools match your search"
                            : "No spools in inventory"}
                    </div>
                ) : (
                    <div className="spools-grid">
                        {filteredSpools.map((spool) => (
                            <SpoolCard
                                key={spool.id}
                                spool={spool}
                                onClick={(id) => navigate(`/spools/${id}`)}
                            />
                        ))}
                    </div>
                )}

                <div className="inventory-stats">
                    <div className="stat">
                        <span className="stat-label">Total Spools:</span>
                        <span className="stat-value">{spools.length}</span>
                    </div>
                    <div className="stat">
                        <span className="stat-label">Total Weight:</span>
                        <span className="stat-value">
                            {spools.reduce((sum, s) => sum + s.current_weight, 0).toFixed(1)}g
                        </span>
                    </div>
                    <div className="stat">
                        <span className="stat-label">Total Available:</span>
                        <span className="stat-value">
                            {spools.reduce((sum, s) => sum + s.available, 0).toFixed(1)}g
                        </span>
                    </div>
                </div>
            </div>

            <Modal
                isOpen={showSpoolForm}
                title="Create Spool"
                onClose={() => setShowSpoolForm(false)}
            >
                <SpoolForm
                    onSuccess={async () => {
                        setShowSpoolForm(false);
                        await loadSpools();
                    }}
                    onCancel={() => setShowSpoolForm(false)}
                />
            </Modal>
        </>
    );
}