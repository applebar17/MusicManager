import { GitCompareArrows } from "lucide-react";

import { EmptyState, Panel, PanelHeader } from "../../shared/ui";

export function MatchingPanel() {
  return (
    <Panel>
      <PanelHeader eyebrow="Matching" title="Review queue" icon={<GitCompareArrows size={18} />} />
      <EmptyState
        title="Matching review is not connected yet"
        description="Wave 3 will add matching run, filters, candidates, playback, and manual mapping."
      />
    </Panel>
  );
}
