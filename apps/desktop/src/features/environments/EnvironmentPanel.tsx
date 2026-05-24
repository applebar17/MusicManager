import { HardDrive } from "lucide-react";

import { useAppState } from "../../shared/state";
import { EmptyState, Panel, PanelHeader } from "../../shared/ui";

export function EnvironmentPanel() {
  const { selectedEnvironmentId } = useAppState();

  return (
    <Panel>
      <PanelHeader eyebrow="Environment" title="Workspace and USB root" icon={<HardDrive size={18} />} />
      {selectedEnvironmentId ? (
        <p className="muted">Selected environment: {selectedEnvironmentId}</p>
      ) : (
        <EmptyState
          title="No environment selected"
          description="Wave 1 will connect this panel to environment list, create, update, archive, and scan actions."
        />
      )}
    </Panel>
  );
}
