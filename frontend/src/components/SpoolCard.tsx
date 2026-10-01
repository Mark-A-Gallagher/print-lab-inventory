// SpoolCard.tsx

import type { Spool, Material } from "../types";
import LowStockBadge from "./LowStockBadge";
import "./SpoolCard.css";

interface SpoolCardProps {
    spool: Spool;
    material?: Material;
    onClick?: (id: number) => void;
}

export default function SpoolCard({
    spool,
    material,
    onClick,
}: SpoolCardProps) {
    const handleClick = () => onClick?.(spool.id);

    return (
        <div className="spool-card" onClick={handleClick}>
            <div className="spool-header">
                <h3>{material?.name ?? `Spool #${spool.id}`}</h3>
                {material?.color && (
                    <span className="material-color">{material.color}</span>
                )}
                <LowStockBadge
                    current={spool.current_weight}
                    threshold={spool.low_stock_threshold}
                />
            </div>

            <div className="spool-stats">
                <div className="stat">
                    <span className="label">Current Weight</span>
                    <span className="value">{spool.current_weight.toFixed(1)}g</span>
                </div>
                <div className="stat">
                    <span className="label">Available</span>
                    <span className="value">{spool.available.toFixed(1)}g</span>
                </div>
                <div className="stat">
                    <span className="label">Reserved</span>
                    <span className="value">{spool.reserved_amount.toFixed(1)}g</span>
                </div>
            </div>

            {spool.current_machine_id && (
                <div className="machine-info">
                    Assigned to Machine #{spool.current_machine_id}
                </div>
            )}
        </div>
    );
}
