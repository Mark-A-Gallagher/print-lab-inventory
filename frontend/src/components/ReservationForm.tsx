// ReservationForm.tsx

import { useState } from "react";
import type { PrintRequest, Spool } from "../types";
import "./ReservationForm.css";

interface ReservationFormProps {
    request: PrintRequest;
    availableSpools: Spool[];
    onReserve: (
        allocations: Array<{ spoolId: number; amount: number }>
    ) => Promise<void>;
    loading?: boolean;
}

export default function ReservationForm({
    request,
    availableSpools,
    onReserve,
    loading = false,
}: ReservationFormProps) {
    const [allocations, setAllocations] = useState(() =>
        Array.from({ length: request.color_count }, () => ({
            spoolId: null as number | null,
            amount: 0,
        }))
    );
    const [error, setError] = useState<string | null>(null);

    const combinedAmount = allocations.reduce(
        (total, allocation) => total + (allocation.amount || 0),
        0
    );

    const validAllocations = allocations.every((allocation) => {
        if (!allocation.spoolId || allocation.amount <= 0) return false;
        const spool = availableSpools.find((item) => item.id === allocation.spoolId);
        return Boolean(spool && allocation.amount <= spool.available);
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (combinedAmount > request.amount_grams) {
            setError(
                `The ${combinedAmount}g allocated exceeds the ticket total of ${request.amount_grams}g.`
            );
            return;
        }

        if (!validAllocations) {
            setError("Select a spool and enter a valid amount for every color.");
            return;
        }

        try {
            await onReserve(
                allocations.map((allocation) => ({
                    spoolId: allocation.spoolId as number,
                    amount: allocation.amount,
                }))
            );
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create reservation");
        }
    };

    const updateAllocation = (
        index: number,
        field: "spoolId" | "amount",
        value: number
    ) => {
        setAllocations((current) =>
            current.map((allocation, allocationIndex) =>
                allocationIndex === index
                    ? {
                        ...allocation,
                        [field]: field === "spoolId" ? (value || null) : value,
                    }
                    : allocation
            )
        );
    };

    return (
        <form className="reservation-form" onSubmit={handleSubmit}>
            <p className="allocation-total">
                Allocated: {combinedAmount.toFixed(1)}g / {request.amount_grams}g
            </p>

            {allocations.map((allocation, index) => {
                const selectedSpool = availableSpools.find(
                    (spool) => spool.id === allocation.spoolId
                );

                return (
                    <div className="color-allocation" key={index}>
                        <h4>Color {index + 1}</h4>
                        <div className="form-group">
                            <label htmlFor={`spool-${index}`}>Select Spool:</label>
                            <select
                                id={`spool-${index}`}
                                value={allocation.spoolId ?? ""}
                                onChange={(e) =>
                                    updateAllocation(index, "spoolId", Number(e.target.value))
                                }
                                disabled={loading}
                            >
                                <option value="">-- Choose a spool --</option>
                                {availableSpools.map((spool) => (
                                    <option key={spool.id} value={spool.id}>
                                        Spool #{spool.id}{spool.color ? ` · ${spool.color}` : ""}{" "}
                                        ({spool.available.toFixed(1)}g available)
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="form-group">
                            <label htmlFor={`amount-${index}`}>
                                Reserve Amount (g):
                            </label>
                            <input
                                id={`amount-${index}`}
                                type="number"
                                min="0.1"
                                step="0.1"
                                value={allocation.amount || ""}
                                onChange={(e) =>
                                    updateAllocation(index, "amount", Number(e.target.value))
                                }
                                disabled={loading}
                                max={selectedSpool?.available ?? request.amount_grams}
                            />
                        </div>

                        {selectedSpool && (
                            <div className="info-text">
                                Available in spool: {selectedSpool.available.toFixed(1)}g
                            </div>
                        )}
                    </div>
                );
            })}

            {error && <div className="error-text">{error}</div>}

            <button
                type="submit"
                disabled={
                    loading ||
                    combinedAmount <= 0 ||
                    combinedAmount > request.amount_grams ||
                    !validAllocations
                }
            >
                {loading ? "Reserving..." : "Reserve Filament"}
            </button>
        </form>
    );
}
