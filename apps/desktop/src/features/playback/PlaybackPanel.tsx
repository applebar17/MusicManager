import { Radio } from "lucide-react";

import { Panel, PanelHeader, StatusBadge } from "../../shared/ui";

export function PlaybackPanel() {
  return (
    <Panel>
      <PanelHeader eyebrow="Playback" title="Local audio preview" icon={<Radio size={18} />} />
      <div className="mini-player-preview">
        <StatusBadge>Idle</StatusBadge>
        <p className="muted">Wave 3 will connect this to backend playback URLs.</p>
      </div>
    </Panel>
  );
}
