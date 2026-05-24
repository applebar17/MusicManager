import { ListMusic } from "lucide-react";

import { useAppState } from "../../shared/state";
import { EmptyState, Panel, PanelHeader } from "../../shared/ui";

export function PlaylistPanel() {
  const { selectedEnvironmentId, selectedPlaylistId } = useAppState();

  return (
    <Panel>
      <PanelHeader
        eyebrow="Playlists"
        title="SoundCloud imports and readiness"
        icon={<ListMusic size={18} />}
      />
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
    </Panel>
  );
}
