// api/client.ts

import type {
    Machine,
    MachineCreate,
    PrintRequest,
    PrintRequestCreate,
    Spool,
    SpoolCreate,
    ReservationCreate,
    InventoryEvent,
} from "../types";

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers ?? {}),
        },
        ...options,
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`API request failed (${response.status}): ${text}`);
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return (await response.json()) as T;
}

export const api = {
    // Spools
    getSpools: () => request<Spool[]>("/spools"),
    getSpool: (id: number) => request<Spool>(`/spools/${id}`),
    createSpool: (payload: SpoolCreate) =>
        request<Spool>("/spools", {
            method: "POST",
            body: JSON.stringify(payload),
        }),
    updateSpoolWeight: (id: number, newTotalWeight: number, userId: string = "system", note?: string) =>
        request<InventoryEvent>(`/spools/${id}/weight`, {
            method: "POST",
            body: JSON.stringify({ new_total_weight: newTotalWeight, user_id: userId, note }),
        }),
    correctSpool: (id: number, relatedEventId: number, note: string) =>
        request<InventoryEvent>(`/spools/${id}/correct`, {
            method: "POST",
            body: JSON.stringify({ related_event_id: relatedEventId, note }),
        }),
    assignSpoolToMachine: (id: number, machineId: number, userId: string = "system") =>
        request<InventoryEvent>(`/spools/${id}/assign`, {
            method: "POST",
            body: JSON.stringify({ machine_id: machineId, user_id: userId }),
        }),
    unassignSpool: (id: number, userId: string = "system") =>
        request<InventoryEvent>(`/spools/${id}/unassign`, {
            method: "POST",
            body: JSON.stringify({ user_id: userId }),
        }),
    deleteSpool: (id: number) =>
        request<void>(`/spools/${id}`, {
            method: "DELETE",
        }),

    // Machines
    getMachines: () => request<Machine[]>("/machines"),
    createMachine: (payload: MachineCreate) =>
        request<Machine>("/machines", {
            method: "POST",
            body: JSON.stringify(payload),
        }),

    // Print Requests
    createPrintRequest: (payload: PrintRequestCreate) =>
        request<PrintRequest>("/requests", {
            method: "POST",
            body: JSON.stringify(payload),
        }),
    getPrintRequests: () => request<PrintRequest[]>("/requests"),
    reserveForRequest: (requestId: number, payload: ReservationCreate) =>
        request(`/requests/${requestId}/reserve`, {
            method: "POST",
            body: JSON.stringify(payload),
        }),
    releaseReservation: (requestId: number, spoolId: number) =>
        request(`/requests/${requestId}/release`, {
            method: "POST",
            body: JSON.stringify({ spool_id: spoolId }),
        }),
    fulfillRequest: (requestId: number, spoolId: number) =>
        request(`/requests/${requestId}/fulfill`, {
            method: "POST",
            body: JSON.stringify({ spool_id: spoolId }),
        }),
};
