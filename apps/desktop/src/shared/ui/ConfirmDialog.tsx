import { AlertTriangle } from "lucide-react";

import { Button } from "./Button";

type ConfirmDialogProps = {
  title: string;
  message: string;
  confirmLabel: string;
  open: boolean;
  confirmationPlaceholder?: string;
  confirmationRequiredValue?: string;
  confirmationValue?: string;
  onCancel: () => void;
  onConfirmationChange?: (value: string) => void;
  onConfirm: () => void;
};

export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  open,
  confirmationPlaceholder,
  confirmationRequiredValue,
  confirmationValue = "",
  onCancel,
  onConfirmationChange,
  onConfirm,
}: ConfirmDialogProps) {
  if (!open) {
    return null;
  }

  const confirmationMatches =
    !confirmationRequiredValue || confirmationValue === confirmationRequiredValue;

  return (
    <div className="dialog-backdrop" role="presentation">
      <div className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <div className="confirm-dialog__icon">
          <AlertTriangle size={20} />
        </div>
        <div>
          <h2 id="dialog-title">{title}</h2>
          <p className="muted">{message}</p>
          {confirmationRequiredValue ? (
            <label className="confirm-dialog__confirmation">
              <span>Type {confirmationRequiredValue} to confirm</span>
              <input
                autoFocus
                placeholder={confirmationPlaceholder}
                value={confirmationValue}
                onChange={(event) => onConfirmationChange?.(event.target.value)}
              />
            </label>
          ) : null}
        </div>
        <div className="confirm-dialog__actions">
          <Button onClick={onCancel}>Cancel</Button>
          <Button disabled={!confirmationMatches} variant="danger" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
