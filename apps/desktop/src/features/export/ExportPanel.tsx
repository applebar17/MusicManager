import { Upload } from "lucide-react";

import { EmptyState } from "../../shared/ui";

export function ExportPanel() {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Export</p>
          <h2>Plan and apply USB mirror</h2>
        </div>
        <Upload size={18} />
      </div>
      <EmptyState
        title="Export preview is waiting for playlist data"
        description="Waves 4 and 5 will add plan preview, confirmation, apply, and result inspection."
      />
    </section>
  );
}
