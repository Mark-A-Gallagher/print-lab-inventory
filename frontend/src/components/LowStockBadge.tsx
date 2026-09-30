// LowStockBadge.tsx

import "./LowStockBadge.css";

interface LowStockBadgeProps {
    current: number;
    threshold: number;
}

export default function LowStockBadge({
    current,
    threshold,
}: LowStockBadgeProps) {
    let status: "green" | "yellow" | "red";

    if (current > threshold) {
        status = "green";
    } else if (current > threshold * 0.5) {
        status = "yellow";
    } else {
        status = "red";
    }

    const statusLabels = {
        green: "OK",
        yellow: "Low",
        red: "Critical",
    };

    return <span className={`badge badge-${status}`}>{statusLabels[status]}</span>;
}
