import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileAudio,
  Link2,
  ListMusic,
  Plus,
  PlayCircle,
  RefreshCw,
  Search,
  ShoppingCart,
  TriangleAlert,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, getApiBaseUrl } from "../../shared/api/http";
import type {
  AudioFileRead,
  MatchStatus,
  PlaylistDetailRead,
  PlaylistItemRead,
  PlaylistSummaryRead,
  SoundCloudPlaylistSyncAllResult,
  SoundCloudPlaylistImportResult,
  SoundCloudTrackDiscoveryRead,
} from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import { Button, EmptyState, ErrorBanner, LoadingState, Panel, StatusBadge } from "../../shared/ui";
import {
  addPlaylistLocalItem,
  getPlaylistDetail,
  importSoundCloudPlaylist,
  listPlaylistLocalFileCandidates,
  listPlaylists,
  removePlaylistLocalItem,
  syncAllSoundCloudPlaylists,
  syncSoundCloudPlaylist,
} from "./api";

export function PlaylistPanel() {
  const { selectedEnvironmentId, selectedPlaylistId, selectPlaylist } = useAppState();
  const [playlists, setPlaylists] = useState<PlaylistSummaryRead[]>([]);
  const [playlistDetail, setPlaylistDetail] = useState<PlaylistDetailRead | null>(null);
  const [importResult, setImportResult] = useState<SoundCloudPlaylistImportResult | null>(null);
  const [syncPlaylistResult, setSyncPlaylistResult] =
    useState<SoundCloudPlaylistImportResult | null>(null);
  const [syncAllResult, setSyncAllResult] = useState<SoundCloudPlaylistSyncAllResult | null>(null);
  const [importUrl, setImportUrl] = useState("");
  const [playlistSearch, setPlaylistSearch] = useState("");
  const [trackSearch, setTrackSearch] = useState("");
  const [trackStatusFilter, setTrackStatusFilter] = useState<TrackStatusFilter>("all");
  const [isLocalDialogOpen, setIsLocalDialogOpen] = useState(false);
  const [localFileCandidates, setLocalFileCandidates] = useState<AudioFileRead[]>([]);
  const [localFileSearch, setLocalFileSearch] = useState("");
  const [isLoadingPlaylists, setIsLoadingPlaylists] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isLoadingLocalFiles, setIsLoadingLocalFiles] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [isSyncingPlaylist, setIsSyncingPlaylist] = useState(false);
  const [isSyncingAll, setIsSyncingAll] = useState(false);
  const [isAddingLocalItem, setIsAddingLocalItem] = useState(false);
  const [removingLocalSongId, setRemovingLocalSongId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedPlaylist = useMemo(
    () => playlists.find((playlist) => playlist.id === selectedPlaylistId) ?? null,
    [playlists, selectedPlaylistId],
  );
  const filteredPlaylists = useMemo(
    () =>
      playlists.filter((playlist) =>
        playlist.name.toLowerCase().includes(playlistSearch.trim().toLowerCase()),
      ),
    [playlistSearch, playlists],
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
      setSyncPlaylistResult(null);
      setSyncAllResult(null);
      selectPlaylist(null);
      return;
    }
    void loadPlaylists(selectedEnvironmentId);
  }, [loadPlaylists, selectPlaylist, selectedEnvironmentId]);

  useEffect(() => {
    setImportResult(null);
    setSyncPlaylistResult(null);
    setSyncAllResult(null);
    setImportUrl("");
    setPlaylistSearch("");
      setTrackSearch("");
      setTrackStatusFilter("all");
      setIsLocalDialogOpen(false);
      setLocalFileCandidates([]);
      setLocalFileSearch("");
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
    setSyncPlaylistResult(null);
    setSyncAllResult(null);
    try {
      const result = await importSoundCloudPlaylist(selectedEnvironmentId, url);
      setImportResult(result);
      setImportUrl("");
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

  async function handleSyncAll() {
    if (!selectedEnvironmentId) {
      setError("Select an environment before syncing SoundCloud playlists.");
      return;
    }
    if (playlists.length === 0) {
      setError("Import at least one SoundCloud playlist before syncing all playlists.");
      return;
    }

    setIsSyncingAll(true);
    setError(null);
    setImportResult(null);
    setSyncPlaylistResult(null);
    setSyncAllResult(null);
    try {
      const result = await syncAllSoundCloudPlaylists(selectedEnvironmentId);
      setSyncAllResult(result);
      const items = await listPlaylists(selectedEnvironmentId);
      setPlaylists(items);
      const playlistId =
        selectedPlaylistId && items.some((item) => item.id === selectedPlaylistId)
          ? selectedPlaylistId
          : items[0]?.id ?? null;
      selectPlaylist(playlistId);
      if (playlistId) {
        setPlaylistDetail(await getPlaylistDetail(selectedEnvironmentId, playlistId));
      } else {
        setPlaylistDetail(null);
      }
    } catch (syncError) {
      setError(errorMessage(syncError));
    } finally {
      setIsSyncingAll(false);
    }
  }

  async function handleSyncSelectedPlaylist() {
    if (!selectedEnvironmentId || !selectedPlaylistId) {
      setError("Select a SoundCloud playlist before syncing it.");
      return;
    }
    if (!selectedPlaylist?.remote_playlist_id) {
      setError("The selected playlist is not backed by SoundCloud.");
      return;
    }

    setIsSyncingPlaylist(true);
    setError(null);
    setImportResult(null);
    setSyncPlaylistResult(null);
    setSyncAllResult(null);
    try {
      const result = await syncSoundCloudPlaylist(selectedEnvironmentId, selectedPlaylistId);
      setSyncPlaylistResult(result);
      const items = await listPlaylists(selectedEnvironmentId);
      setPlaylists(items);
      selectPlaylist(result.playlist_id);
      setPlaylistDetail(await getPlaylistDetail(selectedEnvironmentId, result.playlist_id));
    } catch (syncError) {
      setError(errorMessage(syncError));
    } finally {
      setIsSyncingPlaylist(false);
    }
  }

  async function handleOpenLocalFileDialog() {
    if (!selectedEnvironmentId) {
      setError("Select an environment before adding a local file.");
      return;
    }
    setIsLocalDialogOpen(true);
    setIsLoadingLocalFiles(true);
    setError(null);
    try {
      setLocalFileCandidates(await listPlaylistLocalFileCandidates(selectedEnvironmentId));
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setIsLoadingLocalFiles(false);
    }
  }

  async function handleAddLocalFile(audioFileId: string) {
    if (!selectedEnvironmentId || !selectedPlaylistId) {
      setError("Select a playlist before adding a local file.");
      return;
    }
    setIsAddingLocalItem(true);
    setError(null);
    try {
      const detail = await addPlaylistLocalItem(selectedEnvironmentId, selectedPlaylistId, {
        audio_file_id: audioFileId,
      });
      setPlaylistDetail(detail);
      setPlaylists(await listPlaylists(selectedEnvironmentId));
      setIsLocalDialogOpen(false);
      setLocalFileSearch("");
    } catch (addError) {
      setError(errorMessage(addError));
    } finally {
      setIsAddingLocalItem(false);
    }
  }

  async function handleRemoveLocalItem(songId: string) {
    if (!selectedEnvironmentId || !selectedPlaylistId) {
      setError("Select a playlist before removing a local file.");
      return;
    }
    setRemovingLocalSongId(songId);
    setError(null);
    try {
      const detail = await removePlaylistLocalItem(selectedEnvironmentId, selectedPlaylistId, songId);
      setPlaylistDetail(detail);
      setPlaylists(await listPlaylists(selectedEnvironmentId));
    } catch (removeError) {
      setError(errorMessage(removeError));
    } finally {
      setRemovingLocalSongId(null);
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
            <label className="playlist-search-field">
              <Search size={14} />
              <input
                aria-label="Search playlists"
                placeholder="Search playlists..."
                value={playlistSearch}
                onChange={(event) => setPlaylistSearch(event.target.value)}
              />
            </label>
            {isLoadingPlaylists ? <LoadingState label="Loading playlists" /> : null}
            <div className="playlist-nav-list">
              {filteredPlaylists.map((playlist) => (
                <PlaylistNavItem
                  isSelected={playlist.id === selectedPlaylistId}
                  key={playlist.id}
                  playlist={playlist}
                  onSelect={() => selectPlaylist(playlist.id)}
                />
              ))}
              {!isLoadingPlaylists && playlists.length > 0 && filteredPlaylists.length === 0 ? (
                <div className="playlist-filter-empty">No playlists match this search.</div>
              ) : null}
            </div>
          </aside>

          <main className="playlist-main">
            <ImportPanel
              importResult={importResult}
              importUrl={importUrl}
              isImporting={isImporting}
              isSyncingAll={isSyncingAll}
              playlistCount={playlists.length}
              syncPlaylistResult={syncPlaylistResult}
              syncAllResult={syncAllResult}
              onImportUrlChange={setImportUrl}
              onSyncAll={handleSyncAll}
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
              <PlaylistDetailView
                detail={playlistDetail}
                isSyncingPlaylist={isSyncingPlaylist}
                removingLocalSongId={removingLocalSongId}
                statusFilter={trackStatusFilter}
                summary={selectedPlaylist}
                onSyncPlaylist={handleSyncSelectedPlaylist}
                onOpenAddLocalFile={handleOpenLocalFileDialog}
                onRemoveLocalItem={handleRemoveLocalItem}
                trackSearch={trackSearch}
                onStatusFilterChange={setTrackStatusFilter}
                onTrackSearchChange={setTrackSearch}
              />
            ) : null}
          </main>
        </div>
      )}
      {isLocalDialogOpen ? (
        <LocalFileDialog
          candidates={localFileCandidates}
          isAdding={isAddingLocalItem}
          isLoading={isLoadingLocalFiles}
          query={localFileSearch}
          onAdd={handleAddLocalFile}
          onClose={() => setIsLocalDialogOpen(false)}
          onQueryChange={setLocalFileSearch}
        />
      ) : null}
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
  isSyncingAll: boolean;
  playlistCount: number;
  syncPlaylistResult: SoundCloudPlaylistImportResult | null;
  syncAllResult: SoundCloudPlaylistSyncAllResult | null;
  onImportUrlChange: (url: string) => void;
  onSyncAll: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

function ImportPanel({
  importResult,
  importUrl,
  isImporting,
  isSyncingAll,
  playlistCount,
  syncPlaylistResult,
  syncAllResult,
  onImportUrlChange,
  onSyncAll,
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
        <Button
          className="sync-all-button"
          disabled={isImporting || isSyncingAll || playlistCount === 0}
          type="button"
          onClick={onSyncAll}
        >
          {isSyncingAll ? "Syncing all" : "Sync All"}
        </Button>
      </form>

      {importResult ? <ImportResultSummary result={importResult} /> : null}
      {syncPlaylistResult ? (
        <ImportResultSummary result={syncPlaylistResult} statusLabel="Synced" />
      ) : null}
      {syncAllResult ? <SyncAllResultSummary result={syncAllResult} /> : null}
    </section>
  );
}

function ImportResultSummary({
  result,
  statusLabel = "Imported",
}: {
  result: SoundCloudPlaylistImportResult;
  statusLabel?: string;
}) {
  const warningMessages = importWarningMessages(result.warnings);

  return (
    <div className="import-result">
      <div className="import-result__summary">
        <StatusBadge tone="success">{statusLabel}</StatusBadge>
        <span>{result.playlist_name}</span>
        <span>{formatNumber(result.track_count)} tracks</span>
        <span>{formatNumber(result.added)} added</span>
        <span>{formatNumber(result.removed)} removed</span>
        <span>{formatNumber(result.reactivated)} reactivated</span>
        <span>{formatNumber(result.reordered)} reordered</span>
        <span>{formatNumber(result.metadata_changed)} metadata changed</span>
      </div>
      {warningMessages.length > 0 ? (
        <div className="import-result__warnings">
          <AlertTriangle size={15} />
          <span>{warningMessages.join(" ")}</span>
        </div>
      ) : null}
    </div>
  );
}

function SyncAllResultSummary({ result }: { result: SoundCloudPlaylistSyncAllResult }) {
  const failedItems = result.results.filter((item) => item.status === "failed");

  return (
    <div className="import-result">
      <div className="import-result__summary">
        <StatusBadge tone={result.failed > 0 ? "warning" : "success"}>
          {result.failed > 0 ? "Synced with issues" : "Synced all"}
        </StatusBadge>
        <span>{formatNumber(result.total)} SoundCloud playlists</span>
        <span>{formatNumber(result.succeeded)} synced</span>
        <span>{formatNumber(result.failed)} failed</span>
      </div>
      {failedItems.length > 0 ? (
        <div className="import-result__warnings">
          <AlertTriangle size={15} />
          <span>
            {failedItems
              .map(
                (item) =>
                  `${item.playlist_name ?? "Playlist"}: ${
                    item.error_message ??
                    "Sync failed. If this playlist is private, make it public and try again."
                  }`,
              )
              .join(" ")}
          </span>
        </div>
      ) : null}
    </div>
  );
}

function importWarningMessages(warnings: readonly string[]) {
  const warningSet = new Set(warnings);
  const messages: string[] = [];
  const hadIncompleteHydration = warnings.some(
    (warning) =>
      warning.startsWith("soundcloud_hydration_track_") ||
      warning === "soundcloud_hydration_incomplete_track_data",
  );
  const handledWarnings = new Set<string>(["soundcloud_api_enrichment_used"]);

  if (
    warningSet.has("soundcloud_public_html_no_track_rows") ||
    warningSet.has("soundcloud_api_enrichment_failed") ||
    (hadIncompleteHydration && !warningSet.has("soundcloud_api_enrichment_used"))
  ) {
    messages.push(
      "SoundCloud only exposed part of this playlist. If tracks are missing, make sure the playlist is public and try syncing again.",
    );
  }

  if (warningSet.has("soundcloud_public_html_missing_playlist_title")) {
    messages.push(
      "SoundCloud did not expose the playlist title, so the saved name may use a fallback.",
    );
  }

  for (const warning of warnings) {
    if (
      handledWarnings.has(warning) ||
      warning.startsWith("soundcloud_hydration_track_") ||
      warning === "soundcloud_hydration_incomplete_track_data" ||
      warning === "soundcloud_public_html_no_track_rows" ||
      warning === "soundcloud_api_enrichment_failed" ||
      warning === "soundcloud_public_html_missing_playlist_title"
    ) {
      continue;
    }
    messages.push("Some optional SoundCloud metadata was unavailable.");
    break;
  }

  return [...new Set(messages)];
}

type PlaylistDetailViewProps = {
  detail: PlaylistDetailRead;
  isSyncingPlaylist: boolean;
  removingLocalSongId: string | null;
  statusFilter: TrackStatusFilter;
  summary: PlaylistSummaryRead;
  trackSearch: string;
  onOpenAddLocalFile: () => void;
  onRemoveLocalItem: (songId: string) => void;
  onSyncPlaylist: () => void;
  onStatusFilterChange: (filter: TrackStatusFilter) => void;
  onTrackSearchChange: (query: string) => void;
};

type TrackStatusFilter = "all" | MatchStatus;

function PlaylistDetailView({
  detail,
  isSyncingPlaylist,
  removingLocalSongId,
  statusFilter,
  summary,
  trackSearch,
  onOpenAddLocalFile,
  onRemoveLocalItem,
  onSyncPlaylist,
  onStatusFilterChange,
  onTrackSearchChange,
}: PlaylistDetailViewProps) {
  const filteredItems = useMemo(
    () =>
      detail.items.filter((item) => {
        const query = trackSearch.trim().toLowerCase();
        const matchesText =
          query.length === 0 ||
          item.title.toLowerCase().includes(query) ||
          (item.artist ?? "").toLowerCase().includes(query) ||
          item.song_id.toLowerCase().includes(query);
        const matchesStatus =
          statusFilter === "all" || item.match_status === statusFilter;
        return matchesText && matchesStatus;
      }),
    [detail.items, statusFilter, trackSearch],
  );

  return (
    <section className="playlist-detail">
      <header className="playlist-detail-header">
        <div>
          {summary.remote_playlist_id ? <span className="soundcloud-badge">SoundCloud Import</span> : null}
          <h2>{detail.name}</h2>
          <div className="playlist-chip-row">
            <span className="playlist-chip playlist-chip--neutral">
              {formatNumber(detail.active_item_count)} Tracks
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
                {formatNumber(detail.inactive_item_count)} Removed
              </span>
            ) : null}
          </div>
        </div>
        <div className="playlist-detail-header__actions">
          <Button icon={<Plus size={16} />} type="button" onClick={onOpenAddLocalFile}>
            Add Local File
          </Button>
          {summary.remote_playlist_id ? (
            <Button
              disabled={isSyncingPlaylist}
              icon={<RefreshCw size={16} />}
              variant="primary"
              onClick={onSyncPlaylist}
            >
              {isSyncingPlaylist ? "Syncing" : "Sync Playlist"}
            </Button>
          ) : null}
        </div>
      </header>

      <div className="playlist-detail-tools">
        <label className="playlist-search-field playlist-search-field--wide">
          <Search size={14} />
          <input
            aria-label="Search playlist tracks"
            placeholder="Search title, artist, or song id..."
            value={trackSearch}
            onChange={(event) => onTrackSearchChange(event.target.value)}
          />
        </label>
        <select
          aria-label="Filter playlist tracks by status"
          value={statusFilter}
          onChange={(event) => onStatusFilterChange(event.target.value as TrackStatusFilter)}
        >
          <option value="all">All tracks</option>
          <option value="matched">Matched</option>
          <option value="manually_mapped">Manual</option>
          <option value="missing_audio">Missing</option>
          <option value="ambiguous">Ambiguous</option>
        </select>
        <span>{formatNumber(filteredItems.length)} visible</span>
      </div>

      <div className="playlist-table-wrap">
        <table className="playlist-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Title / Artist</th>
              <th>Source</th>
              <th>Dur</th>
              <th>Status</th>
              <th>Accepted Audio</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((item) => (
              <PlaylistTrackRow
                item={item}
                key={`${item.song_id}-${item.position}`}
                isRemovingLocal={removingLocalSongId === item.song_id}
                onRemoveLocalItem={onRemoveLocalItem}
              />
            ))}
          </tbody>
        </table>
        {filteredItems.length === 0 ? (
          <div className="playlist-filter-empty playlist-filter-empty--table">
            No tracks match the current filters.
          </div>
        ) : null}
      </div>

      <RemovedFromSoundCloudPanel items={detail.removed_items} />
    </section>
  );
}

function PlaylistTrackRow({
  item,
  isRemovingLocal,
  onRemoveLocalItem,
}: {
  item: PlaylistItemRead;
  isRemovingLocal?: boolean;
  onRemoveLocalItem?: (songId: string) => void;
}) {
  const rowClassName = [
    "playlist-track-row",
    item.match_status === "ambiguous" ? "is-ambiguous" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <tr className={rowClassName}>
      <td className="track-position">{item.position}</td>
      <td className="track-title-cell">
        <strong>{item.title}</strong>
        <span>{item.artist ?? "Unknown artist"}</span>
        <em>{playlistItemSourceLabel(item)}</em>
      </td>
      <td>
        <SourceInfoCell discovery={item.source_discovery} />
      </td>
      <td className="track-duration">{formatDuration(item.duration_seconds)}</td>
      <td>
        <MatchStatusPill status={item.match_status} />
      </td>
      <td>
        <AcceptedAudioCell item={item} />
      </td>
      <td>
        {item.local_membership_active && onRemoveLocalItem ? (
          <button
            className="icon-button"
            disabled={isRemovingLocal}
            type="button"
            title="Remove local membership"
            onClick={() => onRemoveLocalItem(item.song_id)}
          >
            <Trash2 size={15} />
          </button>
        ) : null}
      </td>
    </tr>
  );
}

function RemovedFromSoundCloudPanel({ items }: { items: PlaylistItemRead[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <details className="playlist-removed-panel">
      <summary>
        <span>Removed from SoundCloud</span>
        <strong>{formatNumber(items.length)}</strong>
      </summary>
      <div className="playlist-removed-list">
        {items.map((item) => (
          <div className="playlist-removed-row" key={`${item.song_id}-${item.position}`}>
            <span className="track-position">{item.position}</span>
            <span>
              <strong>{item.title}</strong>
              <em>
                {item.artist ?? "Unknown artist"}
                {item.remote_removed_at ? ` · ${formatDateTime(item.remote_removed_at)}` : ""}
              </em>
            </span>
            <MatchStatusPill status={item.match_status} />
            <AcceptedAudioCell item={item} />
          </div>
        ))}
      </div>
    </details>
  );
}

type LocalFileDialogProps = {
  candidates: AudioFileRead[];
  isAdding: boolean;
  isLoading: boolean;
  query: string;
  onAdd: (audioFileId: string) => void;
  onClose: () => void;
  onQueryChange: (query: string) => void;
};

function LocalFileDialog({
  candidates,
  isAdding,
  isLoading,
  query,
  onAdd,
  onClose,
  onQueryChange,
}: LocalFileDialogProps) {
  const filteredCandidates = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return candidates;
    }
    return candidates.filter((file) => {
      const haystack = [
        file.path,
        file.title ?? "",
        file.artist ?? "",
        file.album ?? "",
        audioFileName(file),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [candidates, query]);

  return (
    <div className="playlist-dialog-backdrop">
      <section
        aria-labelledby="playlist-local-file-title"
        aria-modal="true"
        className="playlist-local-dialog"
        role="dialog"
      >
        <header>
          <div>
            <span className="soundcloud-badge">Local File</span>
            <h2 id="playlist-local-file-title">Add Local File</h2>
          </div>
          <button className="icon-button" type="button" title="Close" onClick={onClose}>
            <X size={16} />
          </button>
        </header>
        <label className="playlist-search-field playlist-search-field--wide">
          <Search size={14} />
          <input
            aria-label="Search local files"
            placeholder="Search filename, title, artist, or path..."
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>
        {isLoading ? <LoadingState label="Loading local files" /> : null}
        {!isLoading && filteredCandidates.length === 0 ? (
          <div className="playlist-filter-empty">No scanned active files match this search.</div>
        ) : null}
        <div className="playlist-local-file-list">
          {filteredCandidates.map((file) => (
            <div className="playlist-local-file-row" key={file.id}>
              <FileAudio size={17} />
              <span>
                <strong>{audioFileName(file)}</strong>
                <em>
                  {[file.title, file.artist].filter(Boolean).join(" · ") || file.path}
                </em>
              </span>
              <span>{formatDuration(file.duration_seconds)}</span>
              <Button disabled={isAdding} type="button" onClick={() => onAdd(file.id)}>
                Add
              </Button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function playlistItemSourceLabel(item: PlaylistItemRead) {
  if (item.remote_membership_active && item.local_membership_active) {
    return "Remote + local";
  }
  if (item.local_membership_active) {
    return "Local";
  }
  return "SoundCloud";
}

function SourceInfoCell({ discovery }: { discovery: SoundCloudTrackDiscoveryRead | null }) {
  if (!discovery) {
    return <span className="source-cell source-cell--empty">Not searched</span>;
  }

  const sourceLink = bestSourceLink(discovery);
  return (
    <div className="source-cell">
      <div className="source-cell__actions">
        {sourceLink ? (
          <a href={sourceLink.url} rel="noreferrer" target="_blank">
            <ShoppingCart size={13} />
            {sourceLink.label}
          </a>
        ) : (
          <span>No buy/download link</span>
        )}
        <a href={discovery.track_url} rel="noreferrer" target="_blank" title="Open SoundCloud track">
          <ExternalLink size={13} />
          Track
        </a>
      </div>
      {discovery.description ? (
        <details className="source-cell__description">
          <summary>Description</summary>
          <p>{linkifyText(discovery.description)}</p>
        </details>
      ) : (
        <em>No description stored</em>
      )}
    </div>
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
    const likelyPreview = item.accepted_audio_warnings.includes("likely_preview_download");
    const filename = item.accepted_audio_filename ?? "Accepted audio file";
    const relativePath = item.accepted_audio_relative_path;
    return (
      <div
        className={`accepted-audio ${
          likelyPreview ? "accepted-audio--preview" : "accepted-audio--ready"
        }`}
      >
        <div className="accepted-audio__main">
          {likelyPreview ? (
            <TriangleAlert size={14} />
          ) : item.match_status === "manually_mapped" ? (
            <Link2 size={14} />
          ) : (
            <CheckCircle2 size={14} />
          )}
          <span className="accepted-audio__text">
            <span title={relativePath ?? filename}>{filename}</span>
            {relativePath && relativePath !== filename ? (
              <em title={relativePath}>{relativePath}</em>
            ) : null}
            {likelyPreview ? <strong>Likely preview download</strong> : null}
          </span>
        </div>
        {item.playback_url ? (
          <a
            className="accepted-audio__play"
            href={apiUrl(item.playback_url)}
            rel="noreferrer"
            target="_blank"
            title={`Play ${filename}`}
          >
            <PlayCircle size={14} />
            Play
          </a>
        ) : null}
      </div>
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

function apiUrl(pathOrUrl: string) {
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  return `${getApiBaseUrl()}${pathOrUrl}`;
}

function bestSourceLink(discovery: SoundCloudTrackDiscoveryRead) {
  if (discovery.download_url) {
    return { label: "Download", url: discovery.download_url };
  }
  if (discovery.purchase_url) {
    return { label: discovery.purchase_title ?? "Buy / Download", url: discovery.purchase_url };
  }
  const link = discovery.links.find((item) =>
    ["download", "buy", "buy_or_download"].includes(item.kind),
  );
  if (!link) {
    return null;
  }
  return {
    label: link.kind === "download" ? "Download" : link.kind === "buy" ? "Buy" : "Buy / Download",
    url: link.url,
  };
}

function linkifyText(text: string) {
  const parts = text.split(/(https?:\/\/[^\s)]+|mailto:[^\s)]+)/g);
  return parts.map((part, index) => {
    if (part.startsWith("http://") || part.startsWith("https://") || part.startsWith("mailto:")) {
      return (
        <a href={part} key={`${part}-${index}`} rel="noreferrer" target="_blank">
          {part}
        </a>
      );
    }
    return part;
  });
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

function audioFileName(file: AudioFileRead) {
  return file.path.split(/[\\/]/).pop() || file.path;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
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
