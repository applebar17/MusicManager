import type { ReactNode } from "react";

type PanelProps = {
  children: ReactNode;
  className?: string;
};

export function Panel({ children, className }: PanelProps) {
  return <section className={["panel", className].filter(Boolean).join(" ")}>{children}</section>;
}

type PanelHeaderProps = {
  eyebrow?: string;
  title: string;
  icon?: ReactNode;
};

export function PanelHeader({ eyebrow, title, icon }: PanelHeaderProps) {
  return (
    <div className="panel-header">
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h2>{title}</h2>
      </div>
      {icon}
    </div>
  );
}
