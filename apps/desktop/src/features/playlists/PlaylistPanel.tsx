import {
  AlertTriangle,
  CheckCircle2,
  Link2,
  ListMusic,
  RefreshCw,
  TriangleAlert,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../../shared/api/http";
import type {
  MatchStatus,
  PlaylistDetailRead,
  PlaylistItemRead,
  PlaylistSummaryRead,
  SoundCloudPlaylistImportResult,
} from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import { Button, EmptyState, ErrorBanner, LoadingState, Panel, StatusBadge } from "../../shared/ui";
import { getPlaylistDetail, importSoundCloudPlaylist, listPlaylists } from "./api";

export function PlaylistPanel() {
  const { selectedEnvironmentId, selectedPlaylistId, selectPlaylist } = useAppState();
  const [playlists, setPlaylists] = useState<PlaylistSummaryRead[]>([]);
  const [playlistDetail, setPlaylistDetail] = useState<PlaylistDetailRead | null>(null);
  const [importResult, setImportResult] = useState<SoundCloudPlaylistImportResult | null>(null);
  const [importUrl, setImportUrl] = useState("");
  const [isLoadingPlaylists, setIsLoadingPlaylists] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPlaylist = useMemo(
    () => playlists.find((playlist) => playlist.id === selectedPlaylistId) ?? null,
    [playlists, selectedPlaylistId],
  );

  const loadPlaylists = useCallback(
    async (environmentId: string) => {
      setIsLoadingPlaylists(true);
      setError(null);
      try {
        const items = await listPlaylists(environmentId);
        setPlaylists(items);
        if (!selectedPlaylistId || !items.some((item) => item.id === selectedPlaylistId)) {
          selectPlaylist(items[0]?.id ?? null);
        }
      } catch (loadError) {
        setPlaylists([]);
        setPlaylistDetail(null);
        setError(errorMessage(loadError));
      } finally {
        setIsLoadingPlaylists(false);
      }
    },
    [selectPlaylist, selectedPlaylistId],
  );

  const loadPlaylistDetail = useCallback(async (environmentId: string, playlistId: string) => {
    setIsLoadingDetail(true);
    setError(null);
    try {
      setPlaylistDetail(await getPlaylistDetail(environmentId, playlistId));
    } catch (loadError) {
      setPlaylistDetail(null);
      setError(errorMessage(loadError));
    } finally {
      setIsLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedEnvironmentId) {
      setPlaylists([]);
      setPlaylistDetail(null);
      setImportResult(null);
      selectPlaylist(null);
      return;
    }
    void loadPlaylists(selectedEnvironmentId);
  }, [loadPlaylists, selectPlaylist, selectedEnvironmentId]);

  useEffect(() => {
    setImportResult(null);
    setImportUrl("");
  }, [selectedEnvironmentId]);

  useEffect(() => {
    if (!selectedEnvironmentId || !selectedPlaylistId) {
      setPlaylistDetail(null);
      return;
    }
    void loadPlaylistDetail(selectedEnvironmentId, selectedPlaylistId);
  }, [loadPlaylistDetail, selectedEnvironmentId, selectedPlaylistId]);

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEnvironmentId) {
      setError("Select an environment before importing a SoundCloud playlist.");
      return;
    }

    const url = importUrl.trim();
    if (!url) {
      setError("Paste a public SoundCloud playlist URL before importing.");
      return;
    }

    setIsImporting(true);
    setError(null);
    setImportResult(null);
    try {
      const result = await importSoundCloudPlaylist(selectedEnvironmentId, url);
      setImportResult(result);
      const items = await listPlaylists(selectedEnvironmentId);
      setPlaylists(items);
      selectPlaylist(result.playlist_id);
      setPlaylistDetail(await getPlaylistDetail(selectedEnvironmentId, result.playlist_id));
    } catch (importError) {
      setError(errorMessage(importError));
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <div className="playlist-workspace">
      <PlaylistTopBar />

      {error ? (
        <ErrorBanner
          title="Playlist workspace error"
          message={error}
          actionLabel={selectedEnvironmentId ? "Retry" : undefined}
          onAction={
            selectedEnvironmentId
              ? () => {
                  void loadPlaylists(selectedEnvironmentId);
                  if (selectedPlaylistId) {
                    void loadPlaylistDetail(selectedEnvironmentId, selectedPlaylistId);
                  }
                }
              : undefined
          }
        />
      ) : null}

      {!selectedEnvironmentId ? (
        <Panel className="playlist-empty-panel">
          <EmptyState
            title="Select an environment first"
            description="Create or select an environment from the dashboard before importing SoundCloud playlists."
          />
        </Panel>
      ) : (
        <div className="playlist-browser">
          <aside className="playlist-sidebar-panel">
            <div className="playlist-sidebar-header">
              <span>Your Playlists</span>
            </div>
            {isLoadingPlaylists ? <LoadingState label="Loading playlists" /> : null}
            <div className="playlist-nav-list">
              {playlists.map((playlist) => (
                <PlaylistNavItem
                  isSelected={playlist.id === selectedPlaylistId}
                  key={playlist.id}
                  playlist={playlist}
                  onSelect={() => selectPlaylist(playlist.id)}
                />
              ))}
            </div>
          </aside>

          <main className="playlist-main">
            <ImportPanel
              importResult={importResult}
              importUrl={importUrl}
              isImporting={isImporting}
              onImportUrlChange={setImportUrl}
              onSubmit={handleImport}
            />

            {!isLoadingPlaylists && playlists.length === 0 ? (
              <Panel className="playlist-empty-panel">
                <EmptyState
                  title="No playlists imported yet"
                  description="Paste a public SoundCloud playlist URL to create the first remote-backed playlist for this environment."
                />
              </Panel>
            ) : null}

            {isLoadingDetail ? <LoadingState label="Loading playlist detail" /> : null}

            {selectedPlaylist && playlistDetail ? (
              <PlaylistDetailView detail={playlistDetail} summary={selectedPlaylist} />
            ) : null}
          </main>
        </div>
      )}
    </div>
  );
}

function PlaylistTopBar() {
  return (
    <header className="playlist-topbar">
      <div className="top-tabs" aria-label="Playlist context">
        <span>Environment</span>
        <span className="top-tabs__active">Playlists</span>
      </div>
      <div className="top-actions">
        <button className="icon-button" disabled type="button" title="Folder picker arrives in a later wave">
          <ListMusic size={17} />
        </button>
        <button className="icon-button" disabled type="button" title="Playlist refresh is automatic in Wave 2">
          <RefreshCw size={17} />
        </button>
      </div>
    </header>
  );
}

type PlaylistNavItemProps = {
  playlist: PlaylistSummaryRead;
  isSelected: boolean;
  onSelect: () => void;
};

function PlaylistNavItem({ playlist, isSelected, onSelect }: PlaylistNavItemProps) {
  return (
    <button
      className={["playlist-nav-item", isSelected ? "is-selected" : ""].filter(Boolean).join(" ")}
      type="button"
      onClick={onSelect}
    >
      <ListMusic size={16} />
      <span>{playlist.name}</span>
      {playlist.missing_audio_count + playlist.ambiguous_count > 0 ? (
        <span className="playlist-nav-warning">
          {formatNumber(playlist.missing_audio_count + playlist.ambiguous_count)}
        </span>
      ) : null}
    </button>
  );
}

type ImportPanelProps = {
  importResult: SoundCloudPlaylistImportResult | null;
  importUrl: string;
  isImporting: boolean;
  onImportUrlChange: (url: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

function ImportPanel({
  importResult,
  importUrl,
  isImporting,
  onImportUrlChange,
  onSubmit,
}: ImportPanelProps) {
  return (
    <section className="soundcloud-import-panel">
      <form className="soundcloud-import-form" onSubmit={onSubmit}>
        <Link2 size={17} />
        <input
          aria-label="SoundCloud playlist URL"
          placeholder="Paste a public SoundCloud playlist URL..."
          value={importUrl}
          onChange={(event) => onImportUrlChange(event.target.value)}
        />
        <Button disabled={isImporting} type="submit">
          {isImporting ? "Importing" : "Import / Sync"}
        </Button>
      </form>

      {importResult ? <ImportResultSummary result={importResult} /> : null}
    </section>
  );
}

function ImportResultSummary({ result }: { result: SoundCloudPlaylistImportResult }) {
  return (
    <div className="import-result">
      <div className="import-result__summary">
        <StatusBadge tone="success">Imported</StatusBadge>
        <span>{result.playlist_name}</span>
        <span>{formatNumber(result.track_count)} tracks</span>
        <span>{formatNumber(result.added)} added</span>
        <span>{formatNumber(result.removed)} removed</span>
        <span>{formatNumber(result.reactivated)} reactivated</span>
        <span>{formatNumber(result.reordered)} reordered</span>
        <span>{formatNumber(result.metadata_changed)} metadata changed</span>
      </div>
      {result.warnings.length > 0 ? (
        <div className="import-result__warnings">
          <AlertTriangle size={15} />
          <span>{result.warnings.join(" ")}</span>
        </div>
      ) : null}
    </div>
  );
}

type PlaylistDetailViewProps = {
  detail: PlaylistDetailRead;
  summary: PlaylistSummaryRead;
};

function PlaylistDetailView({ detail, summary }: PlaylistDetailViewProps) {
  return (
    <section className="playlist-detail">
      <header className="playlist-detail-header">
        <div>
          {summary.remote_playlist_id ? <span className="soundcloud-badge">SoundCloud Import</span> : null}
          <h2>{detail.name}</h2>
          <div className="playlist-chip-row">
            <span className="playlist-chip playlist-chip--neutral">
              {formatNumber(detail.active_item_count + detail.inactive_item_count)} Tracks
            </span>
            <span className="playlist-chip playlist-chip--success">
              {formatNumber(summary.matched_count)} Matched
            </span>
            <span className="playlist-chip playlist-chip--danger">
              {formatNumber(summary.missing_audio_count)} Missing
            </span>
            <span className="playlist-chip playlist-chip--warning">
              {formatNumber(summary.ambiguous_count)} Ambiguous
            </span>
            <span className="playlist-chip playlist-chip--accent">
              {formatNumber(summary.manually_mapped_count)} Manual
            </span>
            {detail.inactive_item_count > 0 ? (
              <span className="playlist-chip playlist-chip--neutral">
                {formatNumber(detail.inactive_item_count)} Inactive
              </span>
            ) : null}
          </div>
        </div>
      </header>

      <div className="playlist-table-wrap">
        <table className="playlist-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Title / Artist</th>
              <th>Dur</th>
              <th>Status</th>
              <th>Accepted Audio</th>
            </tr>
          </thead>
          <tbody>
            {detail.items.map((item) => (
              <PlaylistTrackRow item={item} key={`${item.song_id}-${item.position}`} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PlaylistTrackRow({ item }: { item: PlaylistItemRead }) {
  const rowClassName = [
    "playlist-track-row",
    item.match_status === "ambiguous" ? "is-ambiguous" : "",
    !item.remote_membership_active ? "is-inactive" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <tr className={rowClassName}>
      <td className="track-position">{item.position}</td>
      <td className="track-title-cell">
        <strong>{item.title}</strong>
        <span>{item.artist ?? "Unknown artist"}</span>
        {!item.remote_membership_active ? <em>Inactive remote membership</em> : null}
      </td>
      <td className="track-duration">{formatDuration(item.duration_seconds)}</td>
      <td>
        <MatchStatusPill status={item.match_status} />
      </td>
      <td>
        <AcceptedAudioCell item={item} />
      </td>
    </tr>
  );
}

function MatchStatusPill({ status }: { status: MatchStatus }) {
  const toneClass =
    status === "matched"
      ? "matched"
      : status === "missing_audio"
        ? "missing"
        : status === "ambiguous"
          ? "ambiguous"
          : "manual";

  return <span className={`match-pill match-pill--${toneClass}`}>{matchStatusLabel(status)}</span>;
}

function AcceptedAudioCell({ item }: { item: PlaylistItemRead }) {
  if (item.accepted_audio_file_id) {
    return (
      <span className="accepted-audio accepted-audio--ready">
        {item.match_status === "manually_mapped" ? <Link2 size={13} /> : <CheckCircle2 size={13} />}
        <span>{shortId(item.accepted_audio_file_id)}</span>
        {item.playback_url ? <em>playback ready</em> : null}
      </span>
    );
  }

  if (item.match_status === "ambiguous") {
    return (
      <span className="accepted-audio accepted-audio--warning">
        <TriangleAlert size={13} />
        Review needed
      </span>
    );
  }

  return <span className="accepted-audio accepted-audio--empty">No accepted file</span>;
}

function matchStatusLabel(status: MatchStatus) {
  if (status === "missing_audio") {
    return "Missing";
  }
  if (status === "manually_mapped") {
    return "Manual";
  }
  return status[0].toUpperCase() + status.slice(1);
}

function formatDuration(seconds: number | null) {
  if (seconds === null) {
    return "--:--";
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

function shortId(value: string) {
  return value.length > 12 ? `${value.slice(0, 8)}...` : value;
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong while talking to the backend.";
}

function formatNumber(value: number) {
  return new Intl.NumberFormat().format(value);
}
