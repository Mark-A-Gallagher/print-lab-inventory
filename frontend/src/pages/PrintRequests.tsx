// PrintRequests.tsx

import { useEffect, useState } from "react";
import { api } from "../api/client";
import ReservationForm from "../components/ReservationForm";
import Modal from "../components/Modal";
import PrintRequestForm from "../components/PrintRequestForm";
import type { PrintRequest, ReservationEvent, Spool } from "../types";
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
    const [showRequestForm, setShowRequestForm] = useState(false);
    const [reservations, setReservations] = useState<Record<number, ReservationEvent[]>>({});

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

            const reservationEntries = await Promise.all(
                requestsData.map(async (request) => [
                    request.id,
                    await api.getRequestReservations(request.id),
                ] as const)
            );
            setReservations(Object.fromEntries(reservationEntries));
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load data");
        } finally {
            setLoading(false);
        }
    };

    const handleReserve = async (
        allocations: Array<{ spoolId: number; amount: number }>
    ) => {
        if (!selectedRequest) return;

        try {
            setReservationLoading(true);
            await api.reserveRequestBatch(selectedRequest.id, allocations);

            await loadData();
            setSelectedRequest(null);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to reserve");
        } finally {
            setReservationLoading(false);
        }
    };

    const handleMoveToActive = async (requestId: number) => {
        try {
            setReservationLoading(true);
            await api.updateRequestStatus(requestId, "Printing");
            await loadData();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to move ticket to Active");
        } finally {
            setReservationLoading(false);
        }
    };

    const handleComplete = async (requestId: number) => {
        try {
            setReservationLoading(true);
            await api.completeRequest(requestId);
            await loadData();
            setSelectedRequest(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to complete ticket");
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
        completed: requests.filter((r) =>
            ["Complete", "Rejected"].includes(r.status)
        ),
    };

    return (
        <>
            <div className="print-requests">
                <div className="print-requests-header">
                    <h1>Print Requests</h1>
                    <button
                        className="btn-primary"
                        onClick={() => setShowRequestForm(true)}
                    >
                        + Add Request
                    </button>
                </div>

                <div className="requests-container">
                    <div className="requests-list">
                        <div className="request-section">
                            <h2>Pending ({groupedRequests.pending.length})</h2>
                            {groupedRequests.pending.length === 0 ? (
                                <p className="empty-text">No pending requests</p>
                            ) : (
                                <div className="request-cards">
                                    {groupedRequests.pending.map((req) => {
                                        const ticketReservations = reservations[req.id] ?? [];
                                        const isReserved = ticketReservations.length > 0;

                                        return (
                                            <div
                                                key={req.id}
                                                className={`request-card ${selectedRequest?.id === req.id ? "selected" : ""}`}
                                                onClick={() => {
                                                    if (!isReserved) {
                                                        setSelectedRequest(
                                                            selectedRequest?.id === req.id ? null : req
                                                        );
                                                    }
                                                }}
                                            >
                                                <h4>{req.project_name}</h4>
                                                <p className="by">by {req.requested_by}</p>
                                                <p className="amount">Ticket #{req.id}</p>
                                                <p className="amount">Total Filament: {req.amount_grams}g</p>
                                                <p className="amount">Colors: {req.color_count}</p>
                                                {isReserved && (
                                                    <div className="ticket-reservations">
                                                        <strong>Reserved From:</strong>
                                                        {ticketReservations.map((reservation) => (
                                                            <p key={reservation.id}>
                                                                Spool #{reservation.spool_id}: {reservation.amount}g
                                                            </p>
                                                        ))}
                                                        <button
                                                            type="button"
                                                            className="ticket-action"
                                                            disabled={reservationLoading}
                                                            onClick={(event) => {
                                                                event.stopPropagation();
                                                                void handleMoveToActive(req.id);
                                                            }}
                                                        >
                                                            Move to Active
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        <div className="request-section">
                            <h2>Active ({groupedRequests.active.length})</h2>
                            {groupedRequests.active.length === 0 ? (
                                <p className="empty-text">No active requests</p>
                            ) : (
                                <div className="request-cards">
                                    {groupedRequests.active.map((req) => {
                                        const ticketReservations = reservations[req.id] ?? [];
                                        return (
                                            <div key={req.id} className="request-card active">
                                                <h4>{req.project_name}</h4>
                                                <p className="by">by {req.requested_by}</p>
                                                <p className="amount">Ticket #{req.id}</p>
                                                <p className={`status status-${req.status.toLowerCase()}`}>
                                                    {req.status}
                                                </p>
                                                {ticketReservations.length > 0 && (
                                                    <div className="ticket-reservations">
                                                        <strong>Reserved From:</strong>
                                                        {ticketReservations.map((reservation) => (
                                                            <p key={reservation.id}>
                                                                Spool #{reservation.spool_id}: {reservation.amount}g
                                                            </p>
                                                        ))}
                                                    </div>
                                                )}
                                                <button
                                                    type="button"
                                                    className="ticket-action"
                                                    disabled={reservationLoading}
                                                    onClick={() => void handleComplete(req.id)}
                                                >
                                                    Mark Complete
                                                </button>
                                            </div>
                                        );
                                    })}
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

                    {selectedRequest &&
                        (reservations[selectedRequest.id] ?? []).length === 0 &&
                        availableSpools.length > 0 && (
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

            <Modal
                isOpen={showRequestForm}
                title="Create Print Request"
                onClose={() => setShowRequestForm(false)}
            >
                <PrintRequestForm
                    onSuccess={async () => {
                        setShowRequestForm(false);
                        await loadData();
                    }}
                    onCancel={() => setShowRequestForm(false)}
                />
            </Modal>
        </>
    );
}