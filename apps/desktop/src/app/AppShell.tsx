import { Music } from "lucide-react";
import type { ReactNode } from "react";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Music size={24} />
        <h1>Music Manager</h1>
        <p className="muted">Local playlist mirror and USB export workspace.</p>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

