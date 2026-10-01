// Machines.tsx

import { useEffect, useState } from "react";
import { api } from "../api/client";
import Modal from "../components/Modal";
import MachineForm from "../components/MachineForm";
import type { Machine, Spool } from "../types";
import "./Machines.css";

export default function Machines() {
    const [machines, setMachines] = useState<Machine[]>([]);
    const [spools, setSpools] = useState<Spool[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showMachineForm, setShowMachineForm] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setError(null);
            setLoading(true);
            const [machinesData, spoolsData] = await Promise.all([
                api.getMachines(),
                api.getSpools(),
            ]);
            setMachines(machinesData);
            setSpools(spoolsData);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load data");
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="loading">Loading machines...</div>;
    if (error) return <div className="error">Error: {error}</div>;

    const getAssignedSpool = (machineId: number) => {
        return spools.find((s) => s.current_machine_id === machineId);
    };

    return (
        <>
            <div className="machines">
                <div className="machines-header">
                    <h1>3D Printers</h1>
                    <button
                        className="btn-primary"
                        onClick={() => setShowMachineForm(true)}
                    >
                        + Add Machine
                    </button>
                </div>

                {machines.length === 0 ? (
                    <div className="empty-state">No machines configured</div>
                ) : (
                    <div className="machines-grid">
                        {machines.map((machine) => {
                            const assignedSpool = getAssignedSpool(machine.id);

                            return (
                                <div key={machine.id} className="machine-card">
                                    <div className="machine-header">
                                        <h3>{machine.name}</h3>
                                        <span
                                            className={`status-badge status-${machine.status.toLowerCase()}`}
                                        >
                                            {machine.status}
                                        </span>
                                    </div>

                                    <div className="machine-info">
                                        {assignedSpool ? (
                                            <>
                                                <p className="assigned-label">Currently Printing:</p>
                                                <p className="spool-info">
                                                    Spool #{assignedSpool.id}
                                                </p>
                                                <p className="weight-info">
                                                    {assignedSpool.current_weight.toFixed(1)}g available
                                                </p>
                                            </>
                                        ) : (
                                            <p className="no-spool">No filament assigned</p>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            <Modal
                isOpen={showMachineForm}
                title="Create Machine"
                onClose={() => setShowMachineForm(false)}
            >
                <MachineForm
                    onSuccess={async () => {
                        setShowMachineForm(false);
                        await loadData();
                    }}
                    onCancel={() => setShowMachineForm(false)}
                />
            </Modal>
        </>
    );
}