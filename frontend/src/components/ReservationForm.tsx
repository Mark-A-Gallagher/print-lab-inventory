// ReservationForm.tsx

import { useState } from "react";
import type { PrintRequest, Spool } from "../types";
import "./ReservationForm.css";

interface ReservationFormProps {
    request: PrintRequest;
    availableSpools: Spool[];
    onReserve: (spoolId: number, amount: number) => Promise<void>;
    loading?: boolean;
}

export default function ReservationForm({
    request,
    availableSpools,
    onReserve,
    loading = false,
}: ReservationFormProps) {
    const [selectedSpoolId, setSelectedSpoolId] = useState<number | null>(null);
    const [amount, setAmount] = useState(request.amount_required);
    const [error, setError] = useState<string | null>(null);

    const selectedSpool = availableSpools.find((s) => s.id === selectedSpoolId);
    const isValid =
        selectedSpoolId !== null &&
        amount > 0 &&
        amount <= (selectedSpool?.available ?? 0);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!isValid || selectedSpoolId === null) {
            setError("Please select a valid spool and amount");
            return;
        }

        try {
            await onReserve(selectedSpoolId, amount);
            setSelectedSpoolId(null);
            setAmount(request.amount_required);
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Failed to create reservation"
            );
        }
    };

    return (
        <form className="reservation-form" onSubmit={handleSubmit}>
            <div className="form-group">
                <label htmlFor="spool">Select Spool:</label>
                <select
                    id="spool"
                    value={selectedSpoolId ?? ""}
                    onChange={(e) => setSelectedSpoolId(Number(e.target.value) || null)}
                    disabled={loading}
                >
                    <option value="">-- Choose a spool --</option>
                    {availableSpools.map((spool) => (
                        <option key={spool.id} value={spool.id}>
                            Spool #{spool.id} ({spool.available.toFixed(1)}g available)
                        </option>
                    ))}
                </select>
            </div>

            <div className="form-group">
                <label htmlFor="amount">Amount (g):</label>
                <input
                    id="amount"
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(Number(e.target.value))}
                    disabled={loading}
                    max={selectedSpool?.available ?? request.amount_required}
                    step="0.1"
                />
            </div>

            {selectedSpool && (
                <div className="info-text">
                    Available in spool: {selectedSpool.available.toFixed(1)}g
                </div>
            )}

            {error && <div className="error-text">{error}</div>}

            <button type="submit" disabled={!isValid || loading}>
                {loading ? "Reserving..." : "Reserve Filament"}
            </button>
        </form>
    );
}
