import { ListMusic } from "lucide-react";

import { useAppState } from "../../shared/state";
import { EmptyState } from "../../shared/ui";

export function PlaylistPanel() {
  const { selectedEnvironmentId, selectedPlaylistId } = useAppState();

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Playlists</p>
          <h2>SoundCloud imports and readiness</h2>
        </div>
        <ListMusic size={18} />
      </div>
      {selectedEnvironmentId ? (
        <p className="muted">
          Playlist browser ready for environment {selectedEnvironmentId}
          {selectedPlaylistId ? `, playlist ${selectedPlaylistId}` : ""}.
        </p>
      ) : (
        <EmptyState
          title="Select an environment first"
          description="Wave 2 will add playlist import, summaries, and ordered playlist detail."
        />
      )}
    </section>
  );
}
