import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  ExternalLink,
  Library,
  Link2,
  RefreshCw,
  Search,
  ShoppingCart,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, FormEvent } from "react";

import { ApiError } from "../../shared/api/http";
import type {
  LibraryMatchingRunSummary,
  LibraryMatchStatus,
  LibraryTrackCandidateRead,
  MatchReviewRow,
  SoundCloudSourceSyncResultRead,
  SoundCloudTrackDiscoveryRead,
} from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import { Button, EmptyState, ErrorBanner, LoadingState, Panel, StatusBadge } from "../../shared/ui";
import {
  createManualLibraryMapping,
  discoverSoundCloudTrack,
  listManualLibraryTrackCandidates,
  listMatchReview,
  runLibraryMatching,
  syncMissingSoundCloudSources,
} from "./api";

type ReviewFilter =
  | "library_needs_review"
  | "all"
  | "library_matched"
  | "missing_library"
  | "ambiguous_library"
  | "manually_mapped_library";

const DEFAULT_TARGET_COLUMN_WIDTH = 180;

export function MatchingPanel() {
  const { selectedEnvironmentId, openLibraryTrack } = useAppState();
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const [rows, setRows] = useState<MatchReviewRow[]>([]);
  const [filter, setFilter] = useState<ReviewFilter>("library_needs_review");
  const [reviewSearch, setReviewSearch] = useState("");
  const [targetColumnWidth, setTargetColumnWidth] = useState(DEFAULT_TARGET_COLUMN_WIDTH);
  const [libraryRunSummary, setLibraryRunSummary] = useState<LibraryMatchingRunSummary | null>(
    null,
  );
  const [sourceSyncResult, setSourceSyncResult] =
    useState<SoundCloudSourceSyncResultRead | null>(null);
  const [sourceDiscovery, setSourceDiscovery] = useState<SoundCloudTrackDiscoveryRead | null>(null);
  const [sourceDiscoverySongId, setSourceDiscoverySongId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunningLibrary, setIsRunningLibrary] = useState(false);
  const [isDiscoveringSource, setIsDiscoveringSource] = useState(false);
  const [isSyncingSources, setIsSyncingSources] = useState(false);
  const [libraryMappingKey, setLibraryMappingKey] = useState<string | null>(null);
  const [manualLibraryMatchRow, setManualLibraryMatchRow] = useState<MatchReviewRow | null>(null);
  const [manualLibraryCandidateQuery, setManualLibraryCandidateQuery] = useState("");
  const [manualLibraryCandidates, setManualLibraryCandidates] = useState<
    LibraryTrackCandidateRead[]
  >([]);
  const [isSearchingManualLibraryCandidates, setIsSearchingManualLibraryCandidates] =
    useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshReview = useCallback(async (environmentId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      setRows(await listMatchReview(environmentId));
    } catch (loadError) {
      setRows([]);
      setError(errorMessage(loadError));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedEnvironmentId) {
      setRows([]);
      setLibraryRunSummary(null);
      setSourceSyncResult(null);
      setSourceDiscovery(null);
      setSourceDiscoverySongId(null);
      setManualLibraryMatchRow(null);
      setManualLibraryCandidates([]);
      setManualLibraryCandidateQuery("");
      return;
    }
    void refreshReview(selectedEnvironmentId);
  }, [refreshReview, selectedEnvironmentId]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (isEditableTarget(event.target)) {
        return;
      }
      if (event.key === "/") {
        event.preventDefault();
        searchInputRef.current?.focus();
        return;
      }
      if (event.key.toLowerCase() === "r") {
        event.preventDefault();
        if (!isRunningLibrary && selectedEnvironmentId) {
          void handleRunLibraryMatching();
        }
        return;
      }
      if (event.key === "Escape") {
        setReviewSearch("");
        return;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isRunningLibrary, selectedEnvironmentId]);

  const counts = useMemo(() => reviewCounts(rows), [rows]);
  const filteredRows = useMemo(
    () =>
      rows.filter((row) => {
        const query = reviewSearch.trim().toLowerCase();
        const matchesText =
          query.length === 0 ||
          row.title.toLowerCase().includes(query) ||
          (row.artist ?? "").toLowerCase().includes(query) ||
          row.song_id.toLowerCase().includes(query) ||
          (row.library_match
            ? [
                row.library_match.path,
                row.library_match.filename,
                row.library_match.title ?? "",
                row.library_match.artist ?? "",
                row.library_match.method,
              ].some((value) => value.toLowerCase().includes(query))
            : false) ||
          row.library_candidates.some((candidate) =>
            [
              candidate.path,
              candidate.filename,
              candidate.title ?? "",
              candidate.artist ?? "",
              candidate.method,
            ].some((value) => value.toLowerCase().includes(query)),
          );
        if (!matchesText) {
          return false;
        }
        if (filter === "all") {
          return true;
        }
        if (filter === "library_needs_review") {
          return (
            row.library_status === "missing_library" ||
            row.library_status === "ambiguous_library"
          );
        }
        return row.library_status === filter;
      }),
    [filter, reviewSearch, rows],
  );

  async function handleRunLibraryMatching() {
    if (!selectedEnvironmentId) {
      setError("Select an environment before running library matching.");
      return;
    }
    setIsRunningLibrary(true);
    setError(null);
    try {
      const summary = await runLibraryMatching(selectedEnvironmentId);
      setLibraryRunSummary(summary);
      setSourceSyncResult(null);
      await refreshReview(selectedEnvironmentId);
    } catch (runError) {
      setError(errorMessage(runError));
    } finally {
      setIsRunningLibrary(false);
    }
  }

  async function handleMapLibraryCandidate(
    row: MatchReviewRow,
    candidate: LibraryTrackCandidateRead,
  ) {
    if (!selectedEnvironmentId) {
      return;
    }
    const key = `${row.song_id}-${candidate.library_track_id}`;
    setLibraryMappingKey(key);
    setError(null);
    try {
      await createManualLibraryMapping(selectedEnvironmentId, {
        song_id: row.song_id,
        library_track_id: candidate.library_track_id,
      });
      await refreshReview(selectedEnvironmentId);
      if (manualLibraryMatchRow?.song_id === row.song_id) {
        setManualLibraryMatchRow(null);
        setManualLibraryCandidates([]);
        setManualLibraryCandidateQuery("");
      }
    } catch (mappingError) {
      setError(errorMessage(mappingError));
    } finally {
      setLibraryMappingKey(null);
    }
  }

  async function openManualLibraryMatchModal(row: MatchReviewRow) {
    if (!selectedEnvironmentId) {
      return;
    }
    const initialQuery = [row.title, row.artist].filter(Boolean).join(" ");
    setManualLibraryMatchRow(row);
    setManualLibraryCandidateQuery(initialQuery);
    setManualLibraryCandidates([]);
    await loadManualLibraryCandidates(row, initialQuery);
  }

  async function loadManualLibraryCandidates(row: MatchReviewRow, query: string) {
    if (!selectedEnvironmentId) {
      return;
    }
    setIsSearchingManualLibraryCandidates(true);
    setError(null);
    try {
      setManualLibraryCandidates(
        await listManualLibraryTrackCandidates(selectedEnvironmentId, row.song_id, query),
      );
    } catch (candidateError) {
      setManualLibraryCandidates([]);
      setError(errorMessage(candidateError));
    } finally {
      setIsSearchingManualLibraryCandidates(false);
    }
  }

  async function handleManualLibraryCandidateSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (manualLibraryMatchRow) {
      await loadManualLibraryCandidates(manualLibraryMatchRow, manualLibraryCandidateQuery);
    }
  }

  async function handleDiscoverSource(row: MatchReviewRow) {
    if (!selectedEnvironmentId) {
      return;
    }
    setIsDiscoveringSource(true);
    setSourceDiscoverySongId(row.song_id);
    setError(null);
    try {
      setSourceDiscovery(await discoverSoundCloudTrack(selectedEnvironmentId, row.song_id));
      await refreshReview(selectedEnvironmentId);
    } catch (discoveryError) {
      setError(errorMessage(discoveryError));
    } finally {
      setIsDiscoveringSource(false);
    }
  }

  async function handleSyncSources() {
    if (!selectedEnvironmentId) {
      setError("Select an environment before syncing source links.");
      return;
    }
    setIsSyncingSources(true);
    setError(null);
    try {
      const result = await syncMissingSoundCloudSources(selectedEnvironmentId);
      setSourceSyncResult(result);
      setLibraryRunSummary(null);
      await refreshReview(selectedEnvironmentId);
    } catch (syncError) {
      setError(errorMessage(syncError));
    } finally {
      setIsSyncingSources(false);
    }
  }

  return (
    <div className="matching-workspace">
      <header className="matching-topbar">
        <div className="top-tabs" aria-label="Matching context">
          <span>Environment</span>
          <span className="top-tabs__active">Library Matching</span>
        </div>
        <div className="top-actions">
          <button
            className="icon-button"
            disabled={isLoading || !selectedEnvironmentId}
            type="button"
            title="Refresh review"
            onClick={() => {
              if (selectedEnvironmentId) {
                void refreshReview(selectedEnvironmentId);
              }
            }}
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      {error ? (
        <ErrorBanner
          title="Matching review error"
          message={error}
          actionLabel={selectedEnvironmentId ? "Retry" : undefined}
          onAction={
            selectedEnvironmentId
              ? () => {
                  void refreshReview(selectedEnvironmentId);
                }
              : undefined
          }
        />
      ) : null}

      {!selectedEnvironmentId ? (
        <Panel className="matching-empty-panel">
          <EmptyState
            title="Select an environment first"
            description="Create or select an environment, import playlists, and scan audio before reviewing library mappings."
          />
        </Panel>
      ) : (
        <main className="matching-main">
          <section className="matching-header">
            <div>
              <h2>Library Matching Review</h2>
              <p className="muted">Map active SoundCloud playlist songs to shared library tracks.</p>
            </div>
            <div className="matching-header-actions">
              <Button
                disabled={isSyncingSources}
                icon={<ShoppingCart size={18} />}
                onClick={handleSyncSources}
              >
                {isSyncingSources ? "Syncing Sources" : "Sync Sources"}
              </Button>
              <Button
                disabled={isRunningLibrary}
                icon={<Library size={18} />}
                variant="primary"
                onClick={handleRunLibraryMatching}
              >
                {isRunningLibrary ? "Running" : "Run Library Matching"}
              </Button>
            </div>
          </section>

          {libraryRunSummary ? <LibraryRunSummary summary={libraryRunSummary} /> : null}
          {sourceSyncResult ? <SourceSyncSummary result={sourceSyncResult} /> : null}

          <section className="matching-filter-row">
            <div className="matching-filter-group">
              <FilterButton
                active={filter === "library_needs_review"}
                count={counts.library_needs_review}
                label="Needs Review"
                tone="warning"
                onClick={() => setFilter("library_needs_review")}
              />
              <FilterButton
                active={filter === "all"}
                count={counts.all}
                label="All"
                tone="accent"
                onClick={() => setFilter("all")}
              />
              <FilterButton
                active={filter === "library_matched"}
                count={counts.library_matched}
                label="Matched"
                tone="success"
                onClick={() => setFilter("library_matched")}
              />
              <FilterButton
                active={filter === "missing_library"}
                count={counts.missing_library}
                label="Missing"
                tone="danger"
                onClick={() => setFilter("missing_library")}
              />
              <FilterButton
                active={filter === "ambiguous_library"}
                count={counts.ambiguous_library}
                label="Ambiguous"
                tone="warning"
                onClick={() => setFilter("ambiguous_library")}
              />
              <FilterButton
                active={filter === "manually_mapped_library"}
                count={counts.manually_mapped_library}
                label="Manual"
                tone="accent"
                onClick={() => setFilter("manually_mapped_library")}
              />
            </div>
            <label className="matching-search-field">
              <Search size={15} />
              <input
                ref={searchInputRef}
                placeholder="Search songs or library tracks..."
                value={reviewSearch}
                onChange={(event) => setReviewSearch(event.target.value)}
              />
            </label>
            <label className="matching-column-size">
              <span>Target</span>
              <input
                aria-label="Target track column width"
                max={320}
                min={140}
                step={10}
                type="range"
                value={targetColumnWidth}
                onChange={(event) => setTargetColumnWidth(Number(event.target.value))}
              />
            </label>
          </section>

          <section
            className="matching-table matching-table--library"
            style={{ "--target-track-column": `${targetColumnWidth}px` } as CSSProperties}
          >
            <div className="matching-table-header" role="row">
              <span>Target Track</span>
              <span>Artist</span>
              <span>Library Track</span>
              <span>Status</span>
              <span>Actions</span>
            </div>
            {isLoading ? <LoadingState label="Loading library review" /> : null}
            {!isLoading && filteredRows.length === 0 ? (
              <EmptyState
                title="No rows match this view"
                description="Run library matching or adjust the filters."
              />
            ) : null}
            <div className="matching-review-list">
              {filteredRows.map((row) => (
                <LibraryReviewRow
                  isDiscoveringSource={isDiscoveringSource && sourceDiscoverySongId === row.song_id}
                  isMapping={libraryMappingKey}
                  key={row.song_id}
                  row={row}
                  sourceDiscovery={sourceDiscoverySongId === row.song_id ? sourceDiscovery : null}
                  onDiscoverSource={handleDiscoverSource}
                  onMapLibraryCandidate={handleMapLibraryCandidate}
                  onOpenLibraryTrack={openLibraryTrack}
                  onOpenManualLibraryMatch={openManualLibraryMatchModal}
                />
              ))}
            </div>
          </section>
        </main>
      )}

      <ManualLibraryMatchModal
        candidates={manualLibraryCandidates}
        isMapping={libraryMappingKey}
        isSearching={isSearchingManualLibraryCandidates}
        query={manualLibraryCandidateQuery}
        row={manualLibraryMatchRow}
        onClose={() => {
          setManualLibraryMatchRow(null);
          setManualLibraryCandidates([]);
          setManualLibraryCandidateQuery("");
        }}
        onMapCandidate={handleMapLibraryCandidate}
        onOpenLibraryTrack={openLibraryTrack}
        onQueryChange={setManualLibraryCandidateQuery}
        onSearch={handleManualLibraryCandidateSearch}
      />
    </div>
  );
}

function FilterButton({
  active,
  count,
  label,
  tone,
  onClick,
}: {
  active: boolean;
  count: number;
  label: string;
  tone: "accent" | "success" | "warning" | "danger";
  onClick: () => void;
}) {
  return (
    <button
      className={["matching-filter", `matching-filter--${tone}`, active ? "is-active" : ""].join(
        " ",
      )}
      type="button"
      onClick={onClick}
    >
      {label}
      <span>{formatNumber(count)}</span>
    </button>
  );
}

function LibraryRunSummary({ summary }: { summary: LibraryMatchingRunSummary }) {
  return (
    <section className="matching-run-summary">
      <StatusBadge tone="neutral">{`${formatNumber(summary.total)} songs`}</StatusBadge>
      <span>{formatNumber(summary.matched)} matched</span>
      <span>{formatNumber(summary.manually_mapped_library)} manual</span>
      <span>{formatNumber(summary.ambiguous_library)} ambiguous</span>
      <span>{formatNumber(summary.missing_library)} missing</span>
    </section>
  );
}

function SourceSyncSummary({ result }: { result: SoundCloudSourceSyncResultRead }) {
  return (
    <section className="matching-run-summary">
      <StatusBadge tone="neutral">{`${formatNumber(result.total)} checked`}</StatusBadge>
      <span>{formatNumber(result.discovered)} discovered</span>
      <span>{formatNumber(result.skipped)} skipped</span>
      <span>{formatNumber(result.failed)} failed</span>
    </section>
  );
}

type LibraryReviewRowProps = {
  row: MatchReviewRow;
  isDiscoveringSource: boolean;
  isMapping: string | null;
  sourceDiscovery: SoundCloudTrackDiscoveryRead | null;
  onDiscoverSource: (row: MatchReviewRow) => void;
  onMapLibraryCandidate: (row: MatchReviewRow, candidate: LibraryTrackCandidateRead) => void;
  onOpenLibraryTrack: (libraryTrackId: string) => void;
  onOpenManualLibraryMatch: (row: MatchReviewRow) => void;
};

function LibraryReviewRow({
  row,
  isDiscoveringSource,
  isMapping,
  sourceDiscovery,
  onDiscoverSource,
  onMapLibraryCandidate,
  onOpenLibraryTrack,
  onOpenManualLibraryMatch,
}: LibraryReviewRowProps) {
  const status = row.library_status ?? "missing_library";
  const expanded = status === "ambiguous_library" || row.library_candidates.length > 0;

  return (
    <article className={["matching-row", `matching-row--${legacyStatusClass(status)}`].join(" ")}>
      <div className="matching-row-main matching-row-main--library">
        <div className="matching-row-title">
          <LibraryStatusIcon status={status} />
          <div>
            <strong>{row.title}</strong>
            <span>{row.song_id}</span>
          </div>
        </div>
        <span className="matching-row-artist">{row.artist ?? "Unknown artist"}</span>
        <LibraryTrackCell row={row} onOpenLibraryTrack={onOpenLibraryTrack} />
        <div className="matching-status-stack">
          <LibraryMatchStatusPill status={status} />
          <span className="matching-row-duration">{formatDuration(row.duration_seconds)}</span>
        </div>
        <div className="matching-row-actions">
          <Button icon={<Link2 size={15} />} onClick={() => onOpenManualLibraryMatch(row)}>
            Map Track
          </Button>
          <Button
            disabled={isDiscoveringSource}
            icon={<ShoppingCart size={15} />}
            onClick={() => onDiscoverSource(row)}
          >
            {isDiscoveringSource ? "Checking" : "Sources"}
          </Button>
        </div>
      </div>

      {sourceDiscovery?.description ? (
        <details className="matching-source-description" open>
          <summary>SoundCloud source details</summary>
          <p>{linkifyText(sourceDiscovery.description)}</p>
          <SourceLinks discovery={sourceDiscovery} />
        </details>
      ) : null}

      {expanded ? (
        <div className="candidate-list">
          <div className="candidate-list-title">Library candidates</div>
          {row.library_candidates.length > 0 ? (
            row.library_candidates.map((candidate) => (
              <LibraryCandidateCard
                candidate={candidate}
                isMapping={isMapping === `${row.song_id}-${candidate.library_track_id}`}
                key={candidate.library_track_id}
                row={row}
                onMapCandidate={onMapLibraryCandidate}
                onOpenLibraryTrack={onOpenLibraryTrack}
              />
            ))
          ) : (
            <div className="candidate-empty">
              <AlertTriangle size={15} />
              <span>No viable library candidates were found.</span>
            </div>
          )}
        </div>
      ) : null}
    </article>
  );
}

function LibraryTrackCell({
  row,
  onOpenLibraryTrack,
}: {
  row: MatchReviewRow;
  onOpenLibraryTrack: (libraryTrackId: string) => void;
}) {
  if (!row.library_match) {
    return <span className="matching-library-empty">No library track</span>;
  }
  return (
    <div className="accepted-match-row accepted-library-row matching-library-cell">
      <Library size={15} />
      <span>{row.library_match.path}</span>
      <em>
        {confidenceLabel(row.library_match.confidence)} via {methodLabel(row.library_match.method)}
      </em>
      <button
        className="icon-button"
        type="button"
        title="Open in Library"
        onClick={() => onOpenLibraryTrack(row.library_match!.library_track_id)}
      >
        <ExternalLink size={15} />
      </button>
    </div>
  );
}

type LibraryCandidateCardProps = {
  candidate: LibraryTrackCandidateRead;
  row: MatchReviewRow;
  isMapping: boolean;
  onMapCandidate: (row: MatchReviewRow, candidate: LibraryTrackCandidateRead) => void;
  onOpenLibraryTrack: (libraryTrackId: string) => void;
};

function LibraryCandidateCard({
  candidate,
  row,
  isMapping,
  onMapCandidate,
  onOpenLibraryTrack,
}: LibraryCandidateCardProps) {
  return (
    <div className="candidate-card library-candidate-card">
      <div className="candidate-play candidate-play--static" aria-hidden="true">
        <Library size={16} />
      </div>
      <div className="candidate-body">
        <strong>{candidate.path}</strong>
        <span>
          {candidate.title ?? candidate.filename}
          {candidate.artist ? ` - ${candidate.artist}` : ""}
        </span>
        <div>
          <em>{confidenceLabel(candidate.confidence)} match</em>
          <span>Library</span>
          <span>{methodLabel(candidate.method)}</span>
          <span>{formatDuration(candidate.duration_seconds)}</span>
        </div>
      </div>
      <Button
        disabled={isMapping}
        icon={<Library size={15} />}
        onClick={() => onMapCandidate(row, candidate)}
      >
        {isMapping ? "Mapping" : "Map Track"}
      </Button>
      <button
        className="icon-button"
        type="button"
        title="Open in Library"
        onClick={() => onOpenLibraryTrack(candidate.library_track_id)}
      >
        <ExternalLink size={15} />
      </button>
    </div>
  );
}

type ManualLibraryMatchModalProps = {
  candidates: LibraryTrackCandidateRead[];
  isMapping: string | null;
  isSearching: boolean;
  query: string;
  row: MatchReviewRow | null;
  onClose: () => void;
  onMapCandidate: (row: MatchReviewRow, candidate: LibraryTrackCandidateRead) => void;
  onOpenLibraryTrack: (libraryTrackId: string) => void;
  onQueryChange: (query: string) => void;
  onSearch: (event: FormEvent<HTMLFormElement>) => void;
};

function ManualLibraryMatchModal({
  candidates,
  isMapping,
  isSearching,
  query,
  row,
  onClose,
  onMapCandidate,
  onOpenLibraryTrack,
  onQueryChange,
  onSearch,
}: ManualLibraryMatchModalProps) {
  if (!row) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <div
        className="usb-match-dialog manual-match-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="manual-library-match-title"
      >
        <header>
          <div>
            <p className="eyebrow">Map library track</p>
            <h2 id="manual-library-match-title">{row.title}</h2>
            <p className="muted">
              {row.artist ?? "Unknown artist"} - {formatDuration(row.duration_seconds)}
            </p>
          </div>
          {row.library_status ? <LibraryMatchStatusPill status={row.library_status} /> : null}
        </header>

        <form className="usb-match-search" onSubmit={onSearch}>
          <label className="playlist-search-field playlist-search-field--wide">
            <Search size={14} />
            <input
              aria-label="Search library tracks"
              placeholder="Search library tracks..."
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
            />
          </label>
          <Button disabled={isSearching} type="submit">
            {isSearching ? "Searching" : "Search"}
          </Button>
        </form>

        <div className="usb-candidate-list manual-file-candidate-list">
          {isSearching ? <LoadingState label="Searching library tracks" /> : null}
          {!isSearching && candidates.length === 0 ? (
            <EmptyState
              title="No library tracks found"
              description="No active library tracks match this search."
            />
          ) : null}
          {candidates.map((candidate) => (
            <LibraryCandidateCard
              candidate={candidate}
              isMapping={isMapping === `${row.song_id}-${candidate.library_track_id}`}
              key={candidate.library_track_id}
              row={row}
              onMapCandidate={onMapCandidate}
              onOpenLibraryTrack={onOpenLibraryTrack}
            />
          ))}
        </div>

        <footer>
          <Button onClick={onClose}>Close</Button>
        </footer>
      </div>
    </div>
  );
}

function LibraryStatusIcon({ status }: { status: LibraryMatchStatus | "missing_library" }) {
  if (status === "library_matched" || status === "manually_mapped_library") {
    return <CheckCircle2 size={19} />;
  }
  if (status === "ambiguous_library") {
    return <CircleHelp size={19} />;
  }
  return <AlertTriangle size={19} />;
}

function LibraryMatchStatusPill({ status }: { status: LibraryMatchStatus | "missing_library" }) {
  return (
    <span className={`match-pill match-pill--${libraryPillTone(status)}`}>
      {libraryStatusLabel(status)}
    </span>
  );
}

function reviewCounts(rows: MatchReviewRow[]): Record<ReviewFilter, number> {
  const counts: Record<ReviewFilter, number> = {
    library_needs_review: 0,
    all: rows.length,
    library_matched: 0,
    missing_library: 0,
    ambiguous_library: 0,
    manually_mapped_library: 0,
  };
  for (const row of rows) {
    const status = row.library_status ?? "missing_library";
    counts[status] += 1;
    if (status === "missing_library" || status === "ambiguous_library") {
      counts.library_needs_review += 1;
    }
  }
  return counts;
}

function libraryPillTone(status: LibraryMatchStatus | "missing_library") {
  if (status === "library_matched") {
    return "matched";
  }
  if (status === "missing_library") {
    return "missing";
  }
  if (status === "ambiguous_library") {
    return "ambiguous";
  }
  return "manual";
}

function libraryStatusLabel(status: LibraryMatchStatus | "missing_library") {
  const labels: Record<LibraryMatchStatus | "missing_library", string> = {
    library_matched: "Matched",
    missing_library: "Missing",
    ambiguous_library: "Ambiguous",
    manually_mapped_library: "Manual",
  };
  return labels[status];
}

function legacyStatusClass(status: LibraryMatchStatus | "missing_library") {
  if (status === "library_matched") {
    return "matched";
  }
  if (status === "manually_mapped_library") {
    return "manually_mapped";
  }
  if (status === "ambiguous_library") {
    return "ambiguous";
  }
  return "missing_audio";
}

function SourceLinks({ discovery }: { discovery: SoundCloudTrackDiscoveryRead }) {
  const primary = bestSourceLink(discovery);
  const secondary = discovery.links.filter((link) => primary?.url !== link.url).slice(0, 4);
  if (!primary && secondary.length === 0 && discovery.warnings.length === 0) {
    return null;
  }
  return (
    <div className="source-link-stack">
      {primary ? (
        <a href={primary.url} rel="noreferrer" target="_blank">
          {primary.label}
          <ExternalLink size={13} />
        </a>
      ) : null}
      {secondary.map((link) => (
        <a href={link.url} key={`${link.kind}-${link.url}`} rel="noreferrer" target="_blank">
          {sourceLinkKindLabel(link.kind)}
          <ExternalLink size={13} />
        </a>
      ))}
      {discovery.warnings.map((warning) => (
        <span className="source-warning" key={warning}>
          {sourceWarningLabel(warning)}
        </span>
      ))}
    </div>
  );
}

function methodLabel(method: string) {
  return method.replace(/_/g, " ");
}

function confidenceLabel(confidence: number) {
  return `${Math.round(confidence * 100)}%`;
}

function bestSourceLink(discovery: SoundCloudTrackDiscoveryRead | null) {
  if (!discovery) {
    return null;
  }
  if (discovery.download_url) {
    return { label: "Download", url: discovery.download_url };
  }
  if (discovery.purchase_url) {
    return { label: discovery.purchase_title ?? "Buy / Download", url: discovery.purchase_url };
  }
  const link = discovery.links.find((item) =>
    ["download", "buy", "buy_or_download"].includes(item.kind),
  );
  return link ? { label: sourceLinkKindLabel(link.kind), url: link.url } : null;
}

function sourceLinkKindLabel(kind: string) {
  const labels: Record<string, string> = {
    artist_social: "Artist profile",
    buy: "Buy",
    buy_or_download: "Buy / download",
    contact: "Contact",
    download: "Download",
    external: "External link",
    soundcloud_profile: "SoundCloud profile",
  };
  return labels[kind] ?? methodLabel(kind);
}

function sourceWarningLabel(warning: string) {
  const labels: Record<string, string> = {
    free_download_mentioned_without_link:
      "The description mentions a free download, but no public download link was exposed.",
    no_purchase_or_download_link_found: "No buy or download link was found.",
    promotional_low_quality_notice:
      "The description says this upload may be low quality or promotional.",
  };
  return labels[warning] ?? warning.replace(/_/g, " ");
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

function formatDuration(seconds: number | null) {
  if (seconds === null) {
    return "--:--";
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
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

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  const tagName = target.tagName.toLowerCase();
  return (
    tagName === "input" ||
    tagName === "select" ||
    tagName === "textarea" ||
    target.isContentEditable
  );
}
