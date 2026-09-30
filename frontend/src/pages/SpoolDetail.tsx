// SpoolDetail.tsx

import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import LowStockBadge from "../components/LowStockBadge";
import type { Spool, Machine, InventoryEvent } from "../types";
import "./SpoolDetail.css";

export default function SpoolDetail() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const spoolId = id ? Number(id) : null;

    const [spool, setSpool] = useState<Spool | null>(null);
    const [machines, setMachines] = useState<Machine[]>([]);
    const [history, setHistory] = useState<InventoryEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [weightAdjustment, setWeightAdjustment] = useState("");
    const [note, setNote] = useState("");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (!spoolId) {
            setError("Invalid spool ID");
            return;
        }
        loadData();
    }, [spoolId]);

    const loadData = async () => {
        if (!spoolId) return;
        try {
            setError(null);
            setLoading(true);
            const [spoolData, machinesData] = await Promise.all([
                api.getSpool(spoolId),
                api.getMachines(),
            ]);
            setSpool(spoolData);
            setMachines(machinesData);
            // TODO: fetch history from backend when available
            setHistory([]);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load spool");
        } finally {
            setLoading(false);
        }
    };

    const handleWeightUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!spool || !weightAdjustment || submitting) return;

        try {
            setSubmitting(true);
            await api.updateSpoolWeight(spool.id, Number(weightAdjustment), note);
            setWeightAdjustment("");
            setNote("");
            await loadData();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to update weight");
        } finally {
            setSubmitting(false);
        }
    };

    const handleAssignMachine = async (machineId: number) => {
        if (!spool) return;

        try {
            await api.assignSpoolToMachine(spool.id, machineId);
            await loadData();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to assign machine");
        }
    };

    const handleUnassign = async () => {
        if (!spool) return;

        try {
            await api.unassignSpool(spool.id);
            await loadData();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to unassign");
        }
    };

    if (loading) return <div className="loading">Loading spool details...</div>;
    if (error) return <div className="error">Error: {error}</div>;
    if (!spool) return <div className="error">Spool not found</div>;

    const assignedMachine = machines.find(
        (m) => m.id === spool.current_machine_id
    );

    return (
        <div className="spool-detail">
            <button className="back-button" onClick={() => navigate("/inventory")}>
                ← Back to Inventory
            </button>

            <div className="detail-container">
                <div className="main-info">
                    <div className="header-section">
                        <h1>Spool #{spool.id}</h1>
                        <LowStockBadge
                            current={spool.current_weight}
                            threshold={spool.low_stock_threshold}
                        />
                    </div>

                    <div className="stats-section">
                        <div className="stat-item">
                            <label>Current Weight</label>
                            <span className="value">{spool.current_weight.toFixed(1)}g</span>
                        </div>
                        <div className="stat-item">
                            <label>Available</label>
                            <span className="value">{spool.available.toFixed(1)}g</span>
                        </div>
                        <div className="stat-item">
                            <label>Reserved</label>
                            <span className="value">
                                {spool.reserved_amount.toFixed(1)}g
                            </span>
                        </div>
                        <div className="stat-item">
                            <label>Low Stock Threshold</label>
                            <span className="value">
                                {spool.low_stock_threshold.toFixed(1)}g
                            </span>
                        </div>
                    </div>

                    {assignedMachine && (
                        <div className="machine-section">
                            <h3>Currently Assigned</h3>
                            <div className="machine-info">
                                <p className="machine-name">{assignedMachine.name}</p>
                                <p className="machine-status">{assignedMachine.status}</p>
                                <button
                                    className="btn-danger"
                                    onClick={handleUnassign}
                                    disabled={submitting}
                                >
                                    Remove from Machine
                                </button>
                            </div>
                        </div>
                    )}

                    {!assignedMachine && machines.length > 0 && (
                        <div className="machine-section">
                            <h3>Assign to Machine</h3>
                            <div className="machine-list">
                                {machines.map((machine) => (
                                    <button
                                        key={machine.id}
                                        className="machine-button"
                                        onClick={() => handleAssignMachine(machine.id)}
                                        disabled={submitting}
                                    >
                                        {machine.name}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                <div className="actions-sidebar">
                    <div className="action-card">
                        <h3>Record Usage</h3>
                        <form onSubmit={handleWeightUpdate}>
                            <div className="form-group">
                                <label htmlFor="weight">Weight Change (g)</label>
                                <input
                                    id="weight"
                                    type="number"
                                    value={weightAdjustment}
                                    onChange={(e) => setWeightAdjustment(e.target.value)}
                                    step="0.1"
                                    disabled={submitting}
                                    placeholder="e.g., -25.5"
                                />
                            </div>
                            <div className="form-group">
                                <label htmlFor="note">Note (optional)</label>
                                <textarea
                                    id="note"
                                    value={note}
                                    onChange={(e) => setNote(e.target.value)}
                                    disabled={submitting}
                                    rows={3}
                                    placeholder="e.g., Print job completed"
                                />
                            </div>
                            <button type="submit" disabled={!weightAdjustment || submitting}>
                                {submitting ? "Updating..." : "Update Weight"}
                            </button>
                        </form>
                    </div>

                    {history.length > 0 && (
                        <div className="action-card">
                            <h3>Recent Events</h3>
                            <div className="history-list">
                                {history.slice(0, 5).map((event) => (
                                    <div key={event.id} className="history-item">
                                        <p className="event-type">{event.event_type}</p>
                                        <p className="event-time">
                                            {new Date(event.created_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
