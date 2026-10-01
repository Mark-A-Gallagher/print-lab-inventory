import { type ReactNode } from "react";
import "./Modal.css";

interface ModalProps {
    isOpen: boolean;
    title: string;
    children: ReactNode;
    onClose: () => void;
}

export default function Modal({ isOpen, title, children, onClose }: ModalProps) {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>{title}</h2>
                    <button
                        type="button"
                        className="modal-close"
                        onClick={onClose}
                        aria-label="Close modal"
                    >
                        ×
                    </button>
                </div>
                <div className="modal-body">{children}</div>
            </div>
        </div>
    );
}