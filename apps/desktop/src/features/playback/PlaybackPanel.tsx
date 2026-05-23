import { Radio } from "lucide-react";

import { StatusBadge } from "../../shared/ui";

export function PlaybackPanel() {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Playback</p>
          <h2>Local audio preview</h2>
        </div>
        <Radio size={18} />
      </div>
      <div className="mini-player-preview">
        <StatusBadge>Idle</StatusBadge>
        <p className="muted">Wave 3 will connect this to backend playback URLs.</p>
      </div>
    </section>
  );
}
