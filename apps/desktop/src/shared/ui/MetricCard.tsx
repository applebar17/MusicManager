import type { ReactNode } from "react";

type MetricCardTone = "neutral" | "success" | "warning" | "danger" | "accent";

type MetricCardProps = {
  label: string;
  value: string;
  icon?: ReactNode;
  tone?: MetricCardTone;
  footer?: ReactNode;
};

export function MetricCard({
  label,
  value,
  icon,
  tone = "neutral",
  footer,
}: MetricCardProps) {
  return (
    <div className={`metric-card metric-card--${tone}`}>
      <div className="metric-card__header">
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      {footer ? <div className="metric-card__footer">{footer}</div> : null}
    </div>
  );
}
