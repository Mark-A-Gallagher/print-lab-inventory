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
    const [actionError, setActionError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);

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

    const getAssignedSpools = (machineId: number) => {
        return spools.filter((s) => s.current_machine_id === machineId);
    };

    // Errors from remove/delete show inline so the page stays usable.
    const runAction = async (action: () => Promise<void>) => {
        try {
            setBusy(true);
            setActionError(null);
            await action();
            await loadData();
        } catch (err) {
            setActionError(err instanceof Error ? err.message : "Action failed");
        } finally {
            setBusy(false);
        }
    };

    const handleRemoveSpool = (spoolId: number) =>
        runAction(() => api.unassignSpool(spoolId, "system").then(() => undefined));

    const handleDeleteMachine = (machine: Machine) => {
        if (!window.confirm(`Remove "${machine.name}"? This cannot be undone.`)) return;
        return runAction(() => api.deleteMachine(machine.id));
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

                {actionError && <div className="action-error">{actionError}</div>}

                {machines.length === 0 ? (
                    <div className="empty-state">No machines configured</div>
                ) : (
                    <div className="machines-grid">
                        {machines.map((machine) => {
                            const assignedSpools = getAssignedSpools(machine.id);

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
                                        {assignedSpools.length > 0 ? (
                                            assignedSpools.map((spool) => (
                                                <div key={spool.id} className="assigned-spool">
                                                    <p className="assigned-label">Currently Printing:</p>
                                                    <p className="spool-info">
                                                        {spool.material_type ?? "Spool"}
                                                        {spool.color ? ` · ${spool.color}` : ""}
                                                        {` (#${spool.id})`}
                                                    </p>
                                                    <p className="weight-info">
                                                        {spool.current_weight.toFixed(1)}g available
                                                    </p>
                                                    <button
                                                        className="btn-remove-spool"
                                                        onClick={() => handleRemoveSpool(spool.id)}
                                                        disabled={busy}
                                                    >
                                                        Remove filament
                                                    </button>
                                                </div>
                                            ))
                                        ) : (
                                            <p className="no-spool">No filament assigned</p>
                                        )}
                                    </div>

                                    <div className="machine-actions">
                                        <button
                                            className="btn-delete-machine"
                                            onClick={() => handleDeleteMachine(machine)}
                                            disabled={busy || assignedSpools.length > 0}
                                            title={
                                                assignedSpools.length > 0
                                                    ? "Remove the filament first"
                                                    : "Remove this printer"
                                            }
                                        >
                                            Remove printer
                                        </button>
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