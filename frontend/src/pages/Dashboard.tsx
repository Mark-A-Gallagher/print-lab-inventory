// Dashboard.tsx

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Spool, Machine, PrintRequest } from "../types";
import "./Dashboard.css";

export default function Dashboard() {
    const [spools, setSpools] = useState<Spool[]>([]);
    const [machines, setMachines] = useState<Machine[]>([]);
    const [requests, setRequests] = useState<PrintRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadData = async () => {
            try {
                setError(null);
                const [spoolsData, machinesData, requestsData] = await Promise.all([
                    api.getSpools(),
                    api.getMachines(),
                    api.getPrintRequests(),
                ]);
                setSpools(spoolsData);
                setMachines(machinesData);
                setRequests(requestsData);
            } catch (err) {
                setError(err instanceof Error ? err.message : "Failed to load data");
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, []);

    if (loading)
        return <div className="loading">Loading inventory data...</div>;
    if (error) return <div className="error">Error: {error}</div>;

    const lowStockSpools = spools.filter(
        (s) => s.current_weight <= s.low_stock_threshold
    );
    const assignedSpools = spools.filter((s) => s.current_machine_id !== null);
    const pendingRequests = requests.filter((r) => r.status === "Pending");

    return (
        <div className="dashboard">
            <h1>Lab Inventory Dashboard</h1>

            <div className="stats-grid">
                <div className="stat-card">
                    <h3>Total Spools</h3>
                    <div className="stat-value">{spools.length}</div>
                </div>

                <div className="stat-card warning">
                    <h3>Low Stock</h3>
                    <div className="stat-value">{lowStockSpools.length}</div>
                </div>

                <div className="stat-card">
                    <h3>Machines</h3>
                    <div className="stat-value">{machines.length}</div>
                </div>

                <div className="stat-card">
                    <h3>Pending Requests</h3>
                    <div className="stat-value">{pendingRequests.length}</div>
                </div>
            </div>

            {lowStockSpools.length > 0 && (
                <section className="alert-section">
                    <h2>Low Stock Spools ({lowStockSpools.length})</h2>
                    <ul className="low-stock-list">
                        {lowStockSpools.map((spool) => (
                            <li key={spool.id}>
                                Spool #{spool.id}: {spool.current_weight.toFixed(1)}g /
                                {spool.low_stock_threshold}g threshold
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            <section className="info-section">
                <h2>Active Machine Assignments</h2>
                {assignedSpools.length > 0 ? (
                    <ul className="assignment-list">
                        {assignedSpools.map((spool) => (
                            <li key={spool.id}>
                                Spool #{spool.id} → Machine #{spool.current_machine_id} (
                                {spool.current_weight.toFixed(1)}g)
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="empty-state">No spools currently assigned to machines</p>
                )}
            </section>

            <section className="info-section">
                <h2>Pending Requests ({pendingRequests.length})</h2>
                {pendingRequests.length > 0 ? (
                    <ul className="request-list">
                        {pendingRequests.map((req) => (
                            <li key={req.id}>
                                <strong>{req.project_name}</strong> by {req.requested_by} —{" "}
                                {req.amount_required}g needed
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="empty-state">No pending requests</p>
                )}
            </section>
        </div>
    );
}
