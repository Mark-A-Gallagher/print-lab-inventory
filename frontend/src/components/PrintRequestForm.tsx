import { type FormEvent, useState } from "react";
import { api } from "../api/client";
import type { PrintRequestCreate } from "../types";
import "./PrintRequestForm.css";

interface PrintRequestFormProps {
    onSuccess: () => void;
    onCancel: () => void;
}

export default function PrintRequestForm({
    onSuccess,
    onCancel,
}: PrintRequestFormProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [formData, setFormData] = useState<PrintRequestCreate>({
        requested_by: "",
        project_name: "",
        material_id: 1,
        amount_required: 100,
    });

    const handleChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
    ) => {
        const { name, value } = e.target;

        setFormData((prev) => ({
            ...prev,
            [name]:
                name === "material_id" || name === "amount_required"
                    ? Number(value)
                    : value,
        }));
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await api.createPrintRequest(formData);
            onSuccess();
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Failed to create print request"
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <form className="print-request-form" onSubmit={handleSubmit}>
            <div className="form-group">
                <label htmlFor="requested_by">Requested By *</label>
                <input
                    id="requested_by"
                    name="requested_by"
                    type="text"
                    value={formData.requested_by}
                    onChange={handleChange}
                    placeholder="e.g. Jane Student"
                    required
                />
            </div>

            <div className="form-group">
                <label htmlFor="project_name">Project Name *</label>
                <input
                    id="project_name"
                    name="project_name"
                    type="text"
                    value={formData.project_name}
                    onChange={handleChange}
                    placeholder="e.g. Robot Arm 2"
                    required
                />
            </div>

            <div className="form-group">
                <label htmlFor="material_id">Material ID *</label>
                <input
                    id="material_id"
                    name="material_id"
                    type="number"
                    min="1"
                    value={formData.material_id}
                    onChange={handleChange}
                    required
                />
            </div>

            <div className="form-group">
                <label htmlFor="amount_required">Amount Required (g) *</label>
                <input
                    id="amount_required"
                    name="amount_required"
                    type="number"
                    min="1"
                    step="0.1"
                    value={formData.amount_required}
                    onChange={handleChange}
                    required
                />
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={loading}>
                    {loading ? "Creating..." : "Create Request"}
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