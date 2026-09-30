// PrintRequests.tsx

import { useEffect, useState } from "react";
import { api } from "../api/client";
import ReservationForm from "../components/ReservationForm";
import type { PrintRequest, Spool } from "../types";
import "./PrintRequests.css";

export default function PrintRequests() {
    const [requests, setRequests] = useState<PrintRequest[]>([]);
    const [spools, setSpools] = useState<Spool[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedRequest, setSelectedRequest] = useState<PrintRequest | null>(
        null
    );
    const [reservationLoading, setReservationLoading] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setError(null);
            setLoading(true);
            const [requestsData, spoolsData] = await Promise.all([
                api.getPrintRequests(),
                api.getSpools(),
            ]);
            setRequests(requestsData);
            setSpools(spoolsData);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load data");
        } finally {
            setLoading(false);
        }
    };

    const handleReserve = async (spoolId: number, amount: number) => {
        if (!selectedRequest) return;

        try {
            setReservationLoading(true);
            await api.reserveForRequest(selectedRequest.id, {
                spool_id: spoolId,
                amount,
            });

            // Reload data
            await loadData();
            setSelectedRequest(null);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to reserve");
        } finally {
            setReservationLoading(false);
        }
    };

    if (loading) return <div className="loading">Loading requests...</div>;
    if (error) return <div className="error">Error: {error}</div>;

    const availableSpools = spools.filter((s) => s.available > 0);
    const groupedRequests = {
        pending: requests.filter((r) => r.status === "Pending"),
        active: requests.filter((r) => ["Approved", "Printing"].includes(r.status)),
        completed: requests.filter((r) => [
            "Complete",
            "Rejected",
        ].includes(r.status)),
    };

    return (
        <div className="print-requests">
            <h1>Print Requests</h1>

            <div className="requests-container">
                <div className="requests-list">
                    <div className="request-section">
                        <h2>Pending ({groupedRequests.pending.length})</h2>
                        {groupedRequests.pending.length === 0 ? (
                            <p className="empty-text">No pending requests</p>
                        ) : (
                            <div className="request-cards">
                                {groupedRequests.pending.map((req) => (
                                    <div
                                        key={req.id}
                                        className={`request-card ${selectedRequest?.id === req.id ? "selected" : ""}`}
                                        onClick={() =>
                                            setSelectedRequest(
                                                selectedRequest?.id === req.id ? null : req
                                            )
                                        }
                                    >
                                        <h4>{req.project_name}</h4>
                                        <p className="by">by {req.requested_by}</p>
                                        <p className="amount">Amount: {req.amount_required}g</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="request-section">
                        <h2>Active ({groupedRequests.active.length})</h2>
                        {groupedRequests.active.length === 0 ? (
                            <p className="empty-text">No active requests</p>
                        ) : (
                            <div className="request-cards">
                                {groupedRequests.active.map((req) => (
                                    <div key={req.id} className="request-card active">
                                        <h4>{req.project_name}</h4>
                                        <p className="by">by {req.requested_by}</p>
                                        <p className={`status status-${req.status.toLowerCase()}`}>
                                            {req.status}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="request-section">
                        <h2>Completed ({groupedRequests.completed.length})</h2>
                        {groupedRequests.completed.length === 0 ? (
                            <p className="empty-text">No completed requests</p>
                        ) : (
                            <div className="request-cards">
                                {groupedRequests.completed.map((req) => (
                                    <div key={req.id} className="request-card completed">
                                        <h4>{req.project_name}</h4>
                                        <p className="by">by {req.requested_by}</p>
                                        <p className={`status status-${req.status.toLowerCase()}`}>
                                            {req.status}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {selectedRequest && availableSpools.length > 0 && (
                    <div className="reservation-panel">
                        <h3>Reserve Filament for {selectedRequest.project_name}</h3>
                        <ReservationForm
                            request={selectedRequest}
                            availableSpools={availableSpools}
                            onReserve={handleReserve}
                            loading={reservationLoading}
                        />
                    </div>
                )}

                {selectedRequest && availableSpools.length === 0 && (
                    <div className="no-spools-message">
                        No filament available to reserve
                    </div>
                )}
            </div>
        </div>
    );
}
