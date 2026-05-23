import { FolderTree, ListMusic, Music, Radio, RefreshCw, Upload } from "lucide-react";
import type { ReactNode } from "react";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const navItems = [
    { label: "Environment", icon: FolderTree },
    { label: "Playlists", icon: ListMusic },
    { label: "Matching", icon: RefreshCw },
    { label: "Playback", icon: Radio },
    { label: "Export", icon: Upload },
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
              <button className="nav-button" type="button" key={item.label}>
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
