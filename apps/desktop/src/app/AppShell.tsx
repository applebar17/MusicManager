import {
  ClipboardCheck,
  LayoutDashboard,
  ListMusic,
  Music,
  Settings,
  Upload,
} from "lucide-react";
import type { ReactNode } from "react";

import { useAppState } from "../shared/state";
import type { AppView } from "../shared/state";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const { activeView, selectView } = useAppState();
  const navItems: Array<{
    label: string;
    icon: typeof LayoutDashboard;
    view: AppView;
    bottom?: boolean;
    disabled?: boolean;
  }> = [
    { label: "Dashboard", icon: LayoutDashboard, view: "dashboard" },
    { label: "Playlists", icon: ListMusic, view: "playlists" },
    { label: "Matching Review", icon: ClipboardCheck, view: "matching" },
    { label: "Export", icon: Upload, view: "export", disabled: true },
    { label: "Settings", icon: Settings, view: "settings", bottom: true, disabled: true },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <Music size={24} />
          <div>
            <h1>Music Manager</h1>
            <p className="muted">Local playlist mirror and USB export workspace.</p>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="Primary">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={[
                  "nav-button",
                  activeView === item.view ? "is-active" : "",
                  item.bottom ? "nav-button--bottom" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                disabled={item.disabled}
                onClick={() => selectView(item.view)}
                type="button"
                key={item.label}
                title={item.disabled ? "Coming in a later wave" : undefined}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
