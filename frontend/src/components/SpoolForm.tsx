import { type FormEvent, useState } from "react";
import { api } from "../api/client";
import type { SpoolCreate } from "../types";
import "./SpoolForm.css";

interface SpoolFormProps {
    onSuccess: () => void;
    onCancel: () => void;
}

export default function SpoolForm({ onSuccess, onCancel }: SpoolFormProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [formData, setFormData] = useState({
        material_id: 1,
        material_type: "",
        color: "",
        original_weight: 1000,
        empty_spool_weight: 100,
        low_stock_threshold: 200,
    });

    const handleChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
    ) => {
        const { name, value } = e.target;

        setFormData((prev) => ({
            ...prev,
            [name]:
                name === "material_id" ||
                    name === "original_weight" ||
                    name === "empty_spool_weight" ||
                    name === "low_stock_threshold"
                    ? Number(value)
                    : value,
        }));
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await api.createSpool({
                material_id: formData.material_id,
                material_type: formData.material_type || null,
                color: formData.color || null,
                original_weight: formData.original_weight,
                empty_spool_weight: formData.empty_spool_weight,
                low_stock_threshold: formData.low_stock_threshold,
            });
            onSuccess();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create spool");
        } finally {
            setLoading(false);
        }
    };

    return (
        <form className="spool-form" onSubmit={handleSubmit}>
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
                <label htmlFor="material_type">Material Type</label>
                <input
                    id="material_type"
                    name="material_type"
                    type="text"
                    placeholder="e.g., PLA, PETG, ABS"
                    value={formData.material_type}
                    onChange={handleChange}
                />
            </div>

            <div className="form-group">
                <label htmlFor="color">Color</label>
                <input
                    id="color"
                    name="color"
                    type="text"
                    placeholder="e.g., Black, Red, Blue"
                    value={formData.color}
                    onChange={handleChange}
                />
            </div>

            <div className="form-group">
                <label htmlFor="original_weight">
                    Original Filament Weight (g) *
                </label>
                <input
                    id="original_weight"
                    name="original_weight"
                    type="number"
                    min="1"
                    step="0.1"
                    value={formData.original_weight}
                    onChange={handleChange}
                    required
                />
            </div>

            <div className="form-group">
                <label htmlFor="empty_spool_weight">
                    Empty Spool Weight (g) *
                </label>
                <input
                    id="empty_spool_weight"
                    name="empty_spool_weight"
                    type="number"
                    min="0"
                    step="0.1"
                    value={formData.empty_spool_weight}
                    onChange={handleChange}
                    required
                />
            </div>

            <div className="form-group">
                <label htmlFor="low_stock_threshold">
                    Low Stock Threshold (g) *
                </label>
                <input
                    id="low_stock_threshold"
                    name="low_stock_threshold"
                    type="number"
                    min="0"
                    step="0.1"
                    value={formData.low_stock_threshold}
                    onChange={handleChange}
                    required
                />
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={loading}>
                    {loading ? "Creating..." : "Create Spool"}
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
