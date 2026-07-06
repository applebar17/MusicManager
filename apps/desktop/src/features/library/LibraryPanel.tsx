import {
  AlertTriangle,
  Database,
  FolderOpen,
  RefreshCcw,
  Save,
  ScanLine,
  Search,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, MutableRefObject } from "react";

import { ApiError } from "../../shared/api/http";
import type {
  LibraryAlignmentItemRead,
  LibraryAlignmentRunRead,
  LibraryMetadataAssetRead,
  LibraryMetadataImportRunRead,
  LibraryMetadataIndexEntryRead,
  LibraryRead,
  LibraryTrackRead,
} from "../../shared/api/types";
import { pickMusicFolder } from "../../shared/native/folderPicker";
import { useAppState } from "../../shared/state";
import {
  Button,
  EmptyState,
  ErrorBanner,
  LoadingState,
  MetricCard,
  Panel,
  PanelHeader,
} from "../../shared/ui";
import {
  alignLibraryFromEnvironment,
  configureLibrary,
  getLatestLibraryAlignmentRun,
  getLatestLibraryMetadataImportRun,
  getLibrary,
  getLibraryMetadataAssets,
  getLibraryMetadataIndexEntries,
  getLibraryTracks,
  importLibraryMetadataFromEnvironment,
  scanLibrary,
} from "./api";

type LibrarySection = "overview" | "tracks" | "metadata" | "issues";
type TrackStatusFilter = "all" | "active" | "missing";
type TrackMappingFilter = "all" | "mapped" | "unmapped";

type LibraryState =
  | { status: "loading" }
  | { status: "ready"; library: LibraryRead }
  | { status: "error"; message: string };

export function LibraryPanel() {
  const {
    selectedEnvironmentId,
    focusedLibraryTrackId,
    clearFocusedLibraryTrack,
  } = useAppState();
  const [state, setState] = useState<LibraryState>({ status: "loading" });
  const [latestRun, setLatestRun] = useState<LibraryAlignmentRunRead | null>(null);
  const [latestMetadataRun, setLatestMetadataRun] = useState<LibraryMetadataImportRunRead | null>(
    null,
  );
  const [tracks, setTracks] = useState<LibraryTrackRead[]>([]);
  const [metadataAssets, setMetadataAssets] = useState<LibraryMetadataAssetRead[]>([]);
  const [metadataEntries, setMetadataEntries] = useState<LibraryMetadataIndexEntryRead[]>([]);
  const [activeSection, setActiveSection] = useState<LibrarySection>("overview");
  const [trackSearch, setTrackSearch] = useState("");
  const [trackStatusFilter, setTrackStatusFilter] = useState<TrackStatusFilter>("all");
  const [trackMappingFilter, setTrackMappingFilter] = useState<TrackMappingFilter>("all");
  const [metadataSearch, setMetadataSearch] = useState("");
  const [metadataProviderFilter, setMetadataProviderFilter] = useState("all");
  const [metadataAssetTypeFilter, setMetadataAssetTypeFilter] = useState("all");
  const [metadataLinkFilter, setMetadataLinkFilter] = useState<"all" | "linked" | "unlinked">(
    "all",
  );
  const [rootPath, setRootPath] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pickerMessage, setPickerMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [isAligning, setIsAligning] = useState(false);
  const [isImportingMetadata, setIsImportingMetadata] = useState(false);
  const focusedTrackRef = useRef<HTMLTableRowElement | null>(null);

  const loadLibrary = useCallback(() => {
    setState({ status: "loading" });
    setSaveError(null);
    setActionError(null);
    void loadLibraryData()
      .then((data) => {
        setRootPath(data.library.root_path ?? "");
        setLatestRun(data.alignmentRun);
        setLatestMetadataRun(data.metadataRun);
        setTracks(data.tracks);
        setMetadataAssets(data.assets);
        setMetadataEntries(data.entries);
        setState({ status: "ready", library: data.library });
      })
      .catch((error: unknown) => {
        setState({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "The shared library configuration could not be loaded.",
        });
      });
  }, []);

  useEffect(() => {
    loadLibrary();
  }, [loadLibrary]);

  useEffect(() => {
    if (focusedLibraryTrackId) {
      setActiveSection("tracks");
    }
  }, [focusedLibraryTrackId]);

  useEffect(() => {
    if (focusedLibraryTrackId && focusedTrackRef.current) {
      focusedTrackRef.current.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [focusedLibraryTrackId, tracks, activeSection]);

  const refreshInventory = useCallback(async () => {
    const data = await loadLibraryData();
    setRootPath(data.library.root_path ?? "");
    setLatestRun(data.alignmentRun);
    setLatestMetadataRun(data.metadataRun);
    setTracks(data.tracks);
    setMetadataAssets(data.assets);
    setMetadataEntries(data.entries);
    setState({ status: "ready", library: data.library });
  }, []);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedPath = rootPath.trim();
    if (!trimmedPath) {
      setSaveError("Choose an existing readable and writable folder.");
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    void configureLibrary({ root_path: trimmedPath })
      .then(async () => {
        await refreshInventory();
      })
      .catch((error: unknown) => {
        setSaveError(
          error instanceof ApiError
            ? error.message
            : "The shared library path could not be saved.",
        );
      })
      .finally(() => {
        setIsSaving(false);
      });
  };

  const handlePickFolder = () => {
    setPickerMessage(null);
    void pickMusicFolder().then((result) => {
      if (result.status === "selected") {
        setRootPath(result.path);
        return;
      }
      if (result.status === "unavailable") {
        setPickerMessage(result.message);
      }
    });
  };

  const handleScan = () => {
    setIsScanning(true);
    setActionError(null);
    void scanLibrary()
      .then(async () => {
        await refreshInventory();
      })
      .catch((error: unknown) => {
        setActionError(
          error instanceof ApiError ? error.message : "The shared library scan failed.",
        );
      })
      .finally(() => {
        setIsScanning(false);
      });
  };

  const handleAlign = () => {
    if (!selectedEnvironmentId) {
      setActionError("Select a USB environment before aligning the library.");
      return;
    }
    setIsAligning(true);
    setActionError(null);
    void alignLibraryFromEnvironment(selectedEnvironmentId)
      .then(async () => {
        await refreshInventory();
      })
      .catch((error: unknown) => {
        setActionError(
          error instanceof ApiError ? error.message : "The USB library alignment failed.",
        );
      })
      .finally(() => {
        setIsAligning(false);
      });
  };

  const handleMetadataImport = () => {
    if (!selectedEnvironmentId) {
      setActionError("Select a USB environment before importing metadata.");
      return;
    }
    setIsImportingMetadata(true);
    setActionError(null);
    void importLibraryMetadataFromEnvironment(selectedEnvironmentId)
      .then(async () => {
        await refreshInventory();
      })
      .catch((error: unknown) => {
        setActionError(
          error instanceof ApiError ? error.message : "The metadata import failed.",
        );
      })
      .finally(() => {
        setIsImportingMetadata(false);
      });
  };

  const visibleTracks = useMemo(() => {
    const query = trackSearch.trim().toLowerCase();
    return tracks.filter((track) => {
      const matchesText =
        query.length === 0 ||
        [
          track.filename,
          track.path,
          track.title ?? "",
          track.artist ?? "",
          track.normalized_title ?? "",
        ]
          .join(" ")
          .toLowerCase()
          .includes(query);
      const matchesStatus =
        trackStatusFilter === "all" || track.status === trackStatusFilter;
      const matchesMapping =
        trackMappingFilter === "all" ||
        (trackMappingFilter === "mapped" && track.mapped_song_count > 0) ||
        (trackMappingFilter === "unmapped" && track.mapped_song_count === 0);
      return matchesText && matchesStatus && matchesMapping;
    });
  }, [trackMappingFilter, trackSearch, trackStatusFilter, tracks]);

  const visibleAssets = useMemo(() => {
    const query = metadataSearch.trim().toLowerCase();
    return metadataAssets.filter((asset) => {
      const matchesText =
        query.length === 0 ||
        [
          asset.provider,
          asset.asset_type,
          asset.source_path,
          asset.stored_path ?? "",
          asset.status,
          asset.error_message ?? "",
        ]
          .join(" ")
          .toLowerCase()
          .includes(query);
      const matchesProvider =
        metadataProviderFilter === "all" || asset.provider === metadataProviderFilter;
      const matchesType =
        metadataAssetTypeFilter === "all" || asset.asset_type === metadataAssetTypeFilter;
      return matchesText && matchesProvider && matchesType;
    });
  }, [metadataAssetTypeFilter, metadataAssets, metadataProviderFilter, metadataSearch]);

  const visibleEntries = useMemo(() => {
    const query = metadataSearch.trim().toLowerCase();
    return metadataEntries.filter((entry) => {
      const matchesText =
        query.length === 0 ||
        [entry.provider, entry.source_path, entry.entry_key, entry.library_track_id ?? ""]
          .join(" ")
          .toLowerCase()
          .includes(query);
      const matchesProvider =
        metadataProviderFilter === "all" || entry.provider === metadataProviderFilter;
      const matchesLink =
        metadataLinkFilter === "all" ||
        (metadataLinkFilter === "linked" && Boolean(entry.library_track_id)) ||
        (metadataLinkFilter === "unlinked" && !entry.library_track_id);
      return matchesText && matchesProvider && matchesLink;
    });
  }, [metadataEntries, metadataLinkFilter, metadataProviderFilter, metadataSearch]);

  const metadataProviders = useMemo(
    () =>
      Array.from(
        new Set([...metadataAssets.map((asset) => asset.provider), ...metadataEntries.map((entry) => entry.provider)]),
      ).sort(),
    [metadataAssets, metadataEntries],
  );
  const metadataAssetTypes = useMemo(
    () => Array.from(new Set(metadataAssets.map((asset) => asset.asset_type))).sort(),
    [metadataAssets],
  );
  const issues = useMemo(
    () => buildIssueRows(latestRun, metadataAssets),
    [latestRun, metadataAssets],
  );

  if (state.status === "loading") {
    return <LoadingState label="Loading shared library" />;
  }

  if (state.status === "error") {
    return (
      <ErrorBanner
        title="Library unavailable"
        message={state.message}
        actionLabel="Retry"
        onAction={loadLibrary}
      />
    );
  }

  return (
    <div className="stack">
      <section className="library-header">
        <div>
          <p className="eyebrow">Shared Library</p>
          <h2>Source of truth</h2>
          <p className="muted">
            Inspect the shared library, imported metadata, and current library issues.
          </p>
        </div>
        <Button
          icon={<RefreshCcw size={16} />}
          onClick={loadLibrary}
          disabled={isSaving}
          aria-label="Refresh library"
        >
          Refresh
        </Button>
      </section>

      <section className="metric-grid">
        <MetricCard
          label="Configuration"
          value={state.library.configured ? "Ready" : "Not set"}
          icon={<Database size={18} />}
          tone={state.library.configured ? "success" : "warning"}
          footer={state.library.configured ? "Library root saved" : "Choose an existing folder"}
        />
        <MetricCard
          label="Library tracks"
          value={formatNumber(state.library.track_count)}
          icon={<Database size={18} />}
          tone="accent"
          footer={`${formatNumber(state.library.missing_track_count)} missing`}
        />
        <MetricCard
          label="Metadata assets"
          value={formatNumber(state.library.metadata_asset_count)}
          icon={<Database size={18} />}
          tone="neutral"
          footer={`${formatNumber(state.library.metadata_index_entry_count)} indexed entries`}
        />
      </section>

      <nav className="library-segmented-nav" aria-label="Library sections">
        {(["overview", "tracks", "metadata", "issues"] as LibrarySection[]).map((section) => (
          <button
            className={activeSection === section ? "is-active" : ""}
            key={section}
            type="button"
            onClick={() => setActiveSection(section)}
          >
            {sectionLabel(section)}
          </button>
        ))}
      </nav>

      {activeSection === "overview" ? (
        <OverviewSection
          actionError={actionError}
          isAligning={isAligning}
          isImportingMetadata={isImportingMetadata}
          isSaving={isSaving}
          isScanning={isScanning}
          latestMetadataRun={latestMetadataRun}
          latestRun={latestRun}
          library={state.library}
          pickerMessage={pickerMessage}
          rootPath={rootPath}
          saveError={saveError}
          selectedEnvironmentId={selectedEnvironmentId}
          onAlign={handleAlign}
          onMetadataImport={handleMetadataImport}
          onPickFolder={handlePickFolder}
          onRootPathChange={setRootPath}
          onScan={handleScan}
          onSubmit={handleSubmit}
        />
      ) : null}

      {activeSection === "tracks" ? (
        <TracksSection
          focusedLibraryTrackId={focusedLibraryTrackId}
          focusedTrackRef={focusedTrackRef}
          libraryConfigured={state.library.configured}
          mappingFilter={trackMappingFilter}
          search={trackSearch}
          statusFilter={trackStatusFilter}
          tracks={visibleTracks}
          totalTrackCount={tracks.length}
          onClearFocus={clearFocusedLibraryTrack}
          onMappingFilterChange={setTrackMappingFilter}
          onSearchChange={setTrackSearch}
          onStatusFilterChange={setTrackStatusFilter}
        />
      ) : null}

      {activeSection === "metadata" ? (
        <MetadataSection
          assetTypeFilter={metadataAssetTypeFilter}
          assetTypes={metadataAssetTypes}
          assets={visibleAssets}
          entries={visibleEntries}
          linkFilter={metadataLinkFilter}
          libraryConfigured={state.library.configured}
          providerFilter={metadataProviderFilter}
          providers={metadataProviders}
          search={metadataSearch}
          totalAssetCount={metadataAssets.length}
          totalEntryCount={metadataEntries.length}
          onAssetTypeFilterChange={setMetadataAssetTypeFilter}
          onLinkFilterChange={setMetadataLinkFilter}
          onProviderFilterChange={setMetadataProviderFilter}
          onSearchChange={setMetadataSearch}
        />
      ) : null}

      {activeSection === "issues" ? (
        <IssuesSection issues={issues} latestRun={latestRun} libraryConfigured={state.library.configured} />
      ) : null}
    </div>
  );
}

async function loadLibraryData() {
  const [library, alignmentRun, metadataRun] = await Promise.all([
    getLibrary(),
    getLatestLibraryAlignmentRun(),
    getLatestLibraryMetadataImportRun(),
  ]);
  if (!library.configured) {
    return {
      library,
      alignmentRun,
      metadataRun,
      tracks: [],
      assets: [],
      entries: [],
    };
  }
  const [tracks, assets, entries] = await Promise.all([
    getLibraryTracks(),
    getLibraryMetadataAssets(),
    getLibraryMetadataIndexEntries(),
  ]);
  return { library, alignmentRun, metadataRun, tracks, assets, entries };
}

function OverviewSection({
  actionError,
  isAligning,
  isImportingMetadata,
  isSaving,
  isScanning,
  latestMetadataRun,
  latestRun,
  library,
  pickerMessage,
  rootPath,
  saveError,
  selectedEnvironmentId,
  onAlign,
  onMetadataImport,
  onPickFolder,
  onRootPathChange,
  onScan,
  onSubmit,
}: {
  actionError: string | null;
  isAligning: boolean;
  isImportingMetadata: boolean;
  isSaving: boolean;
  isScanning: boolean;
  latestMetadataRun: LibraryMetadataImportRunRead | null;
  latestRun: LibraryAlignmentRunRead | null;
  library: LibraryRead;
  pickerMessage: string | null;
  rootPath: string;
  saveError: string | null;
  selectedEnvironmentId: string | null;
  onAlign: () => void;
  onMetadataImport: () => void;
  onPickFolder: () => void;
  onRootPathChange: (rootPath: string) => void;
  onScan: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <>
      <Panel className="library-actions-panel">
        <PanelHeader eyebrow="Actions" title="Scan and align" icon={<ScanLine size={18} />} />
        <div className="library-action-row">
          <Button
            icon={<ScanLine size={16} />}
            onClick={onScan}
            disabled={!library.configured || isSaving || isScanning || isAligning}
          >
            {isScanning ? "Scanning" : "Scan Library"}
          </Button>
          <Button
            variant="primary"
            icon={<Upload size={16} />}
            onClick={onAlign}
            disabled={
              !library.configured ||
              !selectedEnvironmentId ||
              isSaving ||
              isScanning ||
              isAligning ||
              isImportingMetadata
            }
          >
            {isAligning ? "Aligning" : "Align From Selected USB"}
          </Button>
          <Button
            icon={<Database size={16} />}
            onClick={onMetadataImport}
            disabled={
              !library.configured ||
              !selectedEnvironmentId ||
              isSaving ||
              isScanning ||
              isAligning ||
              isImportingMetadata
            }
          >
            {isImportingMetadata ? "Importing" : "Import Metadata"}
          </Button>
        </div>
        {actionError ? <ErrorBanner title="Library action failed" message={actionError} /> : null}
      </Panel>

      <Panel className="library-config-panel">
        <PanelHeader
          eyebrow="Setup"
          title={library.configured ? "Library folder" : "Configure library folder"}
          icon={<Database size={18} />}
        />
        <form className="environment-form" onSubmit={onSubmit}>
          <label className="field">
            <span>Root path</span>
            <div className="library-path-input-row">
              <input
                value={rootPath}
                onChange={(event) => onRootPathChange(event.target.value)}
                placeholder="C:\\Music\\Library"
                disabled={isSaving}
              />
              <Button
                type="button"
                icon={<FolderOpen size={16} />}
                onClick={onPickFolder}
                disabled={isSaving}
              >
                Browse
              </Button>
            </div>
          </label>
          {pickerMessage ? <p className="muted">{pickerMessage}</p> : null}
          {library.configured ? <p className="muted">Current library: {library.root_path}</p> : null}
          {saveError ? <ErrorBanner title="Library path rejected" message={saveError} /> : null}
          <div className="form-actions">
            <Button
              type="submit"
              variant="primary"
              icon={<Save size={16} />}
              disabled={isSaving}
            >
              {isSaving ? "Saving" : "Save Library"}
            </Button>
          </div>
        </form>
      </Panel>
      {latestRun ? <LatestAlignmentPanel run={latestRun} /> : null}
      {latestMetadataRun ? <LatestMetadataPanel run={latestMetadataRun} /> : null}
    </>
  );
}

function TracksSection({
  focusedLibraryTrackId,
  focusedTrackRef,
  libraryConfigured,
  mappingFilter,
  search,
  statusFilter,
  tracks,
  totalTrackCount,
  onClearFocus,
  onMappingFilterChange,
  onSearchChange,
  onStatusFilterChange,
}: {
  focusedLibraryTrackId: string | null;
  focusedTrackRef: MutableRefObject<HTMLTableRowElement | null>;
  libraryConfigured: boolean;
  mappingFilter: TrackMappingFilter;
  search: string;
  statusFilter: TrackStatusFilter;
  tracks: LibraryTrackRead[];
  totalTrackCount: number;
  onClearFocus: () => void;
  onMappingFilterChange: (filter: TrackMappingFilter) => void;
  onSearchChange: (search: string) => void;
  onStatusFilterChange: (filter: TrackStatusFilter) => void;
}) {
  if (!libraryConfigured) {
    return <EmptyState title="Library not configured" description="Save a library folder before inspecting tracks." />;
  }

  return (
    <Panel className="library-inventory-panel">
      <PanelHeader eyebrow="Inventory" title="Tracks" icon={<Database size={18} />} />
      <div className="library-inventory-toolbar">
        <label className="playlist-search-field playlist-search-field--wide">
          <Search size={14} />
          <input
            aria-label="Search library tracks"
            placeholder="Search filename, path, title, artist, or normalized title..."
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </label>
        <select
          aria-label="Filter library tracks by status"
          value={statusFilter}
          onChange={(event) => onStatusFilterChange(event.target.value as TrackStatusFilter)}
        >
          <option value="all">All status</option>
          <option value="active">Active</option>
          <option value="missing">Missing</option>
        </select>
        <select
          aria-label="Filter library tracks by mapping"
          value={mappingFilter}
          onChange={(event) => onMappingFilterChange(event.target.value as TrackMappingFilter)}
        >
          <option value="all">All mapping</option>
          <option value="mapped">Mapped</option>
          <option value="unmapped">Unmapped</option>
        </select>
        <span>{formatNumber(tracks.length)} of {formatNumber(totalTrackCount)}</span>
        {focusedLibraryTrackId ? (
          <Button type="button" onClick={onClearFocus}>
            Clear Focus
          </Button>
        ) : null}
      </div>
      {tracks.length === 0 ? (
        <EmptyState title="No tracks found" description="No library tracks match the current filters." />
      ) : (
        <div className="library-table-wrap">
          <table className="library-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Title / Artist</th>
                <th>Dur</th>
                <th>Status</th>
                <th>Mapped</th>
                <th>Seen</th>
                <th>Path</th>
              </tr>
            </thead>
            <tbody>
              {tracks.map((track) => {
                const isFocused = track.id === focusedLibraryTrackId;
                return (
                  <tr
                    className={isFocused ? "is-focused" : ""}
                    key={track.id}
                    ref={isFocused ? focusedTrackRef : undefined}
                  >
                    <td><strong>{track.filename}</strong></td>
                    <td>
                      <span>{track.title ?? "Unknown title"}</span>
                      <em>{track.artist ?? "Unknown artist"}</em>
                    </td>
                    <td>{formatDuration(track.duration_seconds)}</td>
                    <td><span className={`library-status-pill library-status-pill--${track.status}`}>{track.status}</span></td>
                    <td>{formatNumber(track.mapped_song_count)}</td>
                    <td>
                      <span>{formatDateTime(track.last_seen_at)}</span>
                      {track.missing_at ? <em>Missing {formatDateTime(track.missing_at)}</em> : null}
                    </td>
                    <td><code>{track.path}</code></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

function MetadataSection({
  assetTypeFilter,
  assetTypes,
  assets,
  entries,
  linkFilter,
  libraryConfigured,
  providerFilter,
  providers,
  search,
  totalAssetCount,
  totalEntryCount,
  onAssetTypeFilterChange,
  onLinkFilterChange,
  onProviderFilterChange,
  onSearchChange,
}: {
  assetTypeFilter: string;
  assetTypes: string[];
  assets: LibraryMetadataAssetRead[];
  entries: LibraryMetadataIndexEntryRead[];
  linkFilter: "all" | "linked" | "unlinked";
  libraryConfigured: boolean;
  providerFilter: string;
  providers: string[];
  search: string;
  totalAssetCount: number;
  totalEntryCount: number;
  onAssetTypeFilterChange: (filter: string) => void;
  onLinkFilterChange: (filter: "all" | "linked" | "unlinked") => void;
  onProviderFilterChange: (filter: string) => void;
  onSearchChange: (search: string) => void;
}) {
  if (!libraryConfigured) {
    return <EmptyState title="Library not configured" description="Save a library folder before inspecting metadata." />;
  }

  return (
    <Panel className="library-inventory-panel">
      <PanelHeader eyebrow="Inventory" title="Metadata" icon={<Database size={18} />} />
      <div className="library-inventory-toolbar">
        <label className="playlist-search-field playlist-search-field--wide">
          <Search size={14} />
          <input
            aria-label="Search library metadata"
            placeholder="Search provider, paths, entry key, or linked track..."
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </label>
        <select
          aria-label="Filter metadata by provider"
          value={providerFilter}
          onChange={(event) => onProviderFilterChange(event.target.value)}
        >
          <option value="all">All providers</option>
          {providers.map((provider) => (
            <option key={provider} value={provider}>{provider}</option>
          ))}
        </select>
        <select
          aria-label="Filter metadata assets by type"
          value={assetTypeFilter}
          onChange={(event) => onAssetTypeFilterChange(event.target.value)}
        >
          <option value="all">All asset types</option>
          {assetTypes.map((assetType) => (
            <option key={assetType} value={assetType}>{assetType}</option>
          ))}
        </select>
        <select
          aria-label="Filter metadata entries by linked track"
          value={linkFilter}
          onChange={(event) => onLinkFilterChange(event.target.value as "all" | "linked" | "unlinked")}
        >
          <option value="all">All entries</option>
          <option value="linked">Linked entries</option>
          <option value="unlinked">Unlinked entries</option>
        </select>
      </div>
      <div className="library-metadata-grids">
        <section>
          <h3>Assets <span>{formatNumber(assets.length)} of {formatNumber(totalAssetCount)}</span></h3>
          {assets.length === 0 ? (
            <p className="muted">No metadata assets match the current filters.</p>
          ) : (
            <div className="library-compact-list">
              {assets.map((asset) => (
                <div className="library-compact-row" key={asset.id}>
                  <strong>{asset.provider} / {asset.asset_type}</strong>
                  <span>{asset.source_path}</span>
                  <em>{asset.stored_path ?? asset.status}</em>
                </div>
              ))}
            </div>
          )}
        </section>
        <section>
          <h3>Index Entries <span>{formatNumber(entries.length)} of {formatNumber(totalEntryCount)}</span></h3>
          {entries.length === 0 ? (
            <p className="muted">No metadata index entries match the current filters.</p>
          ) : (
            <div className="library-compact-list">
              {entries.map((entry) => (
                <div className="library-compact-row" key={entry.id}>
                  <strong>{entry.entry_key}</strong>
                  <span>{entry.source_path}</span>
                  <em>{entry.library_track_id ? `Track ${entry.library_track_id}` : "No linked track"}</em>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </Panel>
  );
}

function IssuesSection({
  issues,
  latestRun,
  libraryConfigured,
}: {
  issues: LibraryIssueRow[];
  latestRun: LibraryAlignmentRunRead | null;
  libraryConfigured: boolean;
}) {
  if (!libraryConfigured) {
    return <EmptyState title="Library not configured" description="Save a library folder before inspecting issues." />;
  }

  return (
    <Panel className="library-inventory-panel">
      <PanelHeader eyebrow="Review" title="Issues" icon={<AlertTriangle size={18} />} />
      {latestRun ? (
        <div className="library-alignment-summary">
          <span>{formatNumber(latestRun.skipped_collision_count)} collisions</span>
          <span>{formatNumber(latestRun.skipped_error_count)} alignment errors</span>
          <span>{formatNumber(latestRun.warning_count)} warnings</span>
        </div>
      ) : null}
      {issues.length === 0 ? (
        <EmptyState title="No issues found" description="Current alignment and metadata inventories have no issue rows." />
      ) : (
        <div className="library-issue-list">
          {issues.map((issue) => (
            <div className="library-alignment-issue" key={issue.id}>
              <strong>{issue.title}</strong>
              <span>{issue.message}</span>
              <small>{issue.detail}</small>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function LatestAlignmentPanel({ run }: { run: LibraryAlignmentRunRead }) {
  const issueItems = alignmentIssueItems(run);
  return (
    <Panel className="library-alignment-panel">
      <PanelHeader eyebrow="Latest alignment" title={alignmentTitle(run)} icon={<Upload size={18} />} />
      <div className="library-alignment-summary">
        <span>{formatNumber(run.scanned_usb_count)} USB files scanned</span>
        <span>{formatNumber(run.copied_count)} copied</span>
        <span>{formatNumber(run.reused_count)} reused</span>
        <span>{formatNumber(run.skipped_collision_count)} collisions</span>
        <span>{formatNumber(run.skipped_error_count)} errors</span>
      </div>
      {issueItems.length > 0 ? (
        <div className="library-alignment-issues">
          {issueItems.map((item) => (
            <div className="library-alignment-issue" key={item.id}>
              <strong>{item.title ?? item.source_path}</strong>
              <span>{item.reason_message ?? item.status}</span>
              <small>{item.source_path}</small>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">No alignment issues in the latest run.</p>
      )}
    </Panel>
  );
}

function LatestMetadataPanel({ run }: { run: LibraryMetadataImportRunRead }) {
  const issueAssets = run.assets.filter((asset) => asset.status !== "copied");
  return (
    <Panel className="library-alignment-panel">
      <PanelHeader
        eyebrow="Latest metadata import"
        title={run.status === "completed_with_issues" ? "Imported with issues" : "Imported"}
        icon={<Database size={18} />}
      />
      <div className="library-alignment-summary">
        <span>{formatNumber(run.asset_count)} assets preserved</span>
        <span>{formatNumber(run.index_entry_count)} index entries</span>
        <span>{formatNumber(run.error_count)} errors</span>
      </div>
      {issueAssets.length > 0 ? (
        <div className="library-alignment-issues">
          {issueAssets.map((asset) => (
            <div className="library-alignment-issue" key={asset.id}>
              <strong>{asset.provider}</strong>
              <span>{asset.error_message ?? asset.status}</span>
              <small>{asset.source_path}</small>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">No metadata import issues in the latest run.</p>
      )}
    </Panel>
  );
}

type LibraryIssueRow = {
  id: string;
  title: string;
  message: string;
  detail: string;
};

function buildIssueRows(
  latestRun: LibraryAlignmentRunRead | null,
  metadataAssets: LibraryMetadataAssetRead[],
): LibraryIssueRow[] {
  return [
    ...(latestRun ? alignmentIssueItems(latestRun).map(alignmentIssueRow) : []),
    ...metadataAssets
      .filter((asset) => asset.status !== "copied")
      .map((asset) => ({
        id: `metadata-${asset.id}`,
        title: `${asset.provider} metadata`,
        message: asset.error_message ?? asset.error_code ?? asset.status,
        detail: asset.source_path,
      })),
  ];
}

function alignmentIssueItems(run: LibraryAlignmentRunRead) {
  return run.items.filter((item) =>
    ["skipped_collision", "skipped_error", "warning_identity_incomplete"].includes(item.status),
  );
}

function alignmentIssueRow(item: LibraryAlignmentItemRead): LibraryIssueRow {
  return {
    id: `alignment-${item.id}`,
    title: item.title ?? item.source_path,
    message: item.reason_message ?? item.reason_code ?? item.status,
    detail: item.source_path,
  };
}

function alignmentTitle(run: LibraryAlignmentRunRead) {
  if (run.status === "failed") {
    return "Failed";
  }
  return run.status === "completed_with_issues" ? "Completed with issues" : "Completed";
}

function sectionLabel(section: LibrarySection) {
  const labels: Record<LibrarySection, string> = {
    overview: "Overview",
    tracks: "Tracks",
    metadata: "Metadata",
    issues: "Issues",
  };
  return labels[section];
}

function formatNumber(value: number) {
  return new Intl.NumberFormat().format(value);
}

function formatDuration(seconds: number | null) {
  if (seconds === null) {
    return "-";
  }
  const minutes = Math.floor(seconds / 60);
  const remainder = String(seconds % 60).padStart(2, "0");
  return `${minutes}:${remainder}`;
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
