import { GitCompareArrows } from "lucide-react";

import { EmptyState } from "../../shared/ui";

export function MatchingPanel() {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Matching</p>
          <h2>Review queue</h2>
        </div>
        <GitCompareArrows size={18} />
      </div>
      <EmptyState
        title="Matching review is not connected yet"
        description="Wave 3 will add matching run, filters, candidates, playback, and manual mapping."
      />
    </section>
  );
}
