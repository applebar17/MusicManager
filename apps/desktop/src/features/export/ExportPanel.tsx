import { Upload } from "lucide-react";

import { EmptyState, Panel, PanelHeader } from "../../shared/ui";

export function ExportPanel() {
  return (
    <Panel>
      <PanelHeader eyebrow="Export" title="Plan and apply USB mirror" icon={<Upload size={18} />} />
      <EmptyState
        title="Export preview is waiting for playlist data"
        description="Waves 4 and 5 will add plan preview, confirmation, apply, and result inspection."
      />
    </Panel>
  );
}
