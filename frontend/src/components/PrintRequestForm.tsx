import { type FormEvent, useState } from "react";
import { api } from "../api/client";
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
    const [formData, setFormData] = useState({
        id: 1,
        requested_by: "",
        project_name: "",
        amount_grams: 100,
        color_count: 1,
    });

    const handleChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
    ) => {
        const { name, value } = e.target;

        setFormData((prev) => ({
            ...prev,
            [name]:
                name === "id" ||
                    name === "amount_grams" ||
                    name === "color_count"
                    ? Number(value)
                    : value,
        }));
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await api.createPrintRequest({
                id: formData.id,
                requested_by: formData.requested_by,
                project_name: formData.project_name,
                amount_grams: formData.amount_grams,
                color_count: formData.color_count,
            });
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
                <label htmlFor="id">Ticket Number *</label>
                <input
                    id="id"
                    name="id"
                    type="number"
                    min="1"
                    value={formData.id}
                    onChange={handleChange}
                    required
                />
            </div>

            <div className="form-group">
                <label htmlFor="amount_grams">Total Filament (g) *</label>
                <input
                    id="amount_grams"
                    name="amount_grams"
                    type="number"
                    min="1"
                    step="0.1"
                    value={formData.amount_grams}
                    onChange={handleChange}
                    required
                />
            </div>

            <div className="form-group">
                <label htmlFor="color_count">Color Count *</label>
                <input
                    id="color_count"
                    name="color_count"
                    type="number"
                    min="1"
                    value={formData.color_count}
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