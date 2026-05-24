import { AlertTriangle } from "lucide-react";

import { Button } from "./Button";

type ConfirmDialogProps = {
  title: string;
  message: string;
  confirmLabel: string;
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  open,
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <div className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <div className="confirm-dialog__icon">
          <AlertTriangle size={20} />
        </div>
        <div>
          <h2 id="dialog-title">{title}</h2>
          <p className="muted">{message}</p>
        </div>
        <div className="confirm-dialog__actions">
          <Button onClick={onCancel}>Cancel</Button>
          <Button variant="danger" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
