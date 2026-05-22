import { EnvironmentPanel } from "../features/environments/EnvironmentPanel";
import { ExportPanel } from "../features/export/ExportPanel";
import { MatchingPanel } from "../features/matching/MatchingPanel";
import { PlaybackPanel } from "../features/playback/PlaybackPanel";
import { PlaylistPanel } from "../features/playlists/PlaylistPanel";

export function Dashboard() {
  return (
    <div className="stack">
      <EnvironmentPanel />
      <PlaylistPanel />
      <MatchingPanel />
      <PlaybackPanel />
      <ExportPanel />
    </div>
  );
}

