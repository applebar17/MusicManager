import { AppShell } from "./AppShell";
import { Dashboard } from "./Dashboard";
import { AppStateProvider } from "../shared/state";

export function App() {
  return (
    <AppStateProvider>
      <AppShell>
        <Dashboard />
      </AppShell>
    </AppStateProvider>
  );
}
