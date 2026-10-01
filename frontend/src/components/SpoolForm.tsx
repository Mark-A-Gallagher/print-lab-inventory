import { FormEvent, useState } from "react";
import { api } from "../api/client";
import type { SpoolCreate, Material } from "../types";
import "./SpoolForm.css";

interface SpoolFormProps {
    materials: Material[];
    onSuccess: () => void;
    onCancel: () => void;
}

export default function SpoolForm({
    materials,
    onSuccess,
    onCancel,
}: SpoolFormProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [formData, setFormData] = useState<SpoolCreate>({
        material_id: materials[0]?.id ?? 0,
        original_filament_weight: 1000,
        empty_spool_weight: 100,
        low_stock_threshold: 200,
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelect>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]:
                name === "material_id"
                    ? Number(value)
                    : Number(value),
        }));
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await api.createSpool(formData);
            onSuccess();
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Failed to create spool"
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <form className="spool-form" onSubmit={handleSubmit}>
            <div className="form-group">
                <label htmlFor="material_id">Material *</label>
                <select
                    id="material_id"
                    name="material_id"
                    value={formData.material_id}
                    onChange={handleChange}
                    required
                >
                    <option value="">-- Select a material --</option>
                    {materials.map((material) => (
                        <option key={material.id} value={material.id}>
                            {material.name}
                            {material.color ? ` (${material.color})` : ""}
                        </option>
                    ))}
                </select>
            </div>

            <div className="form-group">
                <label htmlFor="original_filament_weight">
                    Original Filament Weight (g) *
                </label>
                <input
                    id="original_filament_weight"
                    name="original_filament_weight"
                    type="number"
                    min="1"
                    step="0.1"
                    value={formData.original_filament_weight}
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
                <button
                    type="submit"
                    className="btn-primary"
                    disabled={loading || materials.length === 0}
                >
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
