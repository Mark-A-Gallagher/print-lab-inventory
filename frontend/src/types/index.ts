// types/index.ts

export type Material = {
    id: number;
    name: string;
    color?: string | null;
};

export type Machine = {
    id: number;
    name: string;
    status: string;
};

export type Spool = {
    id: number;
    material_id: number;
    original_filament_weight: number;
    empty_spool_weight: number;
    low_stock_threshold: number;

    // Derived values from backend event stream
    current_weight: number;
    current_machine_id: number | null;
    reserved_amount: number;
    available: number;
};

export type PrintRequest = {
    id: number;
    requested_by: string;
    project_name: string;
    material_id: number;
    amount_required: number;
    status: "Pending" | "Approved" | "Printing" | "Complete" | "Rejected";
};

export type SpoolCreate = {
    material_id: number;
    material_type?: string | null;
    color?: string | null;
    original_weight: number;
    empty_spool_weight: number;
    low_stock_threshold: number;
};

export type MachineCreate = {
    name: string;
    status?: string;
};

export type PrintRequestCreate = {
    requested_by: string;
    project_name: string;
    material_id: number;
    amount_grams: number;
};

export type ReservationCreate = {
    spool_id: number;
    amount: number;
};

export type InventoryEvent = {
    id: number;
    spool_id: number;
    event_type: string;
    quantity_change?: number | null;
    machine_id?: number | null;
    user_id: string;
    related_event_id?: number | null;
    related_request_id?: number | null;
    note?: string;
    created_at: string;
};

export type ReservationEvent = {
    id: number;
    spool_id: number;
    print_request_id: number;
    event_type: string;
    amount: number;
    user_id: string;
    related_event_id?: number | null;
    created_at: string;
};
