import { type FormEvent, useState } from "react";
import { api } from "../api/client";
import "./MachineForm.css";

interface MachineFormProps {
    onSuccess: () => void;
    onCancel: () => void;
}

export default function MachineForm({ onSuccess, onCancel }: MachineFormProps) {
    const [name, setName] = useState("");
    const [spoolCapacity, setSpoolCapacity] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await api.createMachine({
                name,
                spool_capacity: spoolCapacity,
            });
            onSuccess();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create machine");
        } finally {
            setLoading(false);
        }
    };

    return (
        <form className="machine-form" onSubmit={handleSubmit}>
            <div className="form-group">
                <label htmlFor="machine-name">Machine Name *</label>
                <input
                    id="machine-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Printer 1"
                    required
                />
            </div>

            <div className="form-group">
                <label htmlFor="spool-capacity">Number of Spool Slots *</label>
                <input
                    id="spool-capacity"
                    type="number"
                    min={1}
                    max={100}
                    value={spoolCapacity}
                    onChange={(e) => {
                        const value = Number(e.target.value);
                        setSpoolCapacity(Number.isFinite(value) ? value : 1);
                    }}
                    required
                />
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={loading}>
                    {loading ? "Creating..." : "Create Machine"}
                </button>
                <button
                    type="button"
                    className="btn-secondary"
                    onClick={onCancel}
                    disabled={loading}
                >
                    Cancel
                </button>
            </div>
        </form>
    );
}