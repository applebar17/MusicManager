import { HardDrive } from "lucide-react";

import { useAppState } from "../../shared/state";
import { EmptyState } from "../../shared/ui";

export function EnvironmentPanel() {
  const { selectedEnvironmentId } = useAppState();

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Environment</p>
          <h2>Workspace and USB root</h2>
        </div>
        <HardDrive size={18} />
      </div>
      {selectedEnvironmentId ? (
        <p className="muted">Selected environment: {selectedEnvironmentId}</p>
      ) : (
        <EmptyState
          title="No environment selected"
          description="Wave 1 will connect this panel to environment list, create, update, archive, and scan actions."
        />
      )}
    </section>
  );
}
