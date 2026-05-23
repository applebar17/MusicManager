import { AlertTriangle, RefreshCcw } from "lucide-react";

type ErrorBannerProps = {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function ErrorBanner({ title, message, actionLabel, onAction }: ErrorBannerProps) {
  return (
    <div className="error-banner" role="alert">
      <AlertTriangle size={18} />
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
      </div>
      {actionLabel && onAction ? (
        <button className="icon-button" type="button" onClick={onAction}>
          <RefreshCcw size={15} />
          <span>{actionLabel}</span>
        </button>
      ) : null}
    </div>
  );
}
