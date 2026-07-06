import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  Download,
  ExternalLink,
  Library,
  Link2,
  Play,
  RefreshCw,
  Search,
  ShoppingCart,
  X,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, RefObject } from "react";

import { ApiError } from "../../shared/api/http";
import type {
  DownloadMatchRunResultRead,
  EnvironmentRead,
  LibraryMatchingRunSummary,
  LibraryMatchStatus,
  LibraryTrackCandidateRead,
  MatchCandidateRead,
  MatchingRunSummary,
  MatchReviewRow,
  MatchStatus,
  SoundCloudSourceSyncResultRead,
  SoundCloudTrackDiscoveryRead,
} from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import { Button, EmptyState, ErrorBanner, LoadingState, Panel, StatusBadge } from "../../shared/ui";
import { listEnvironments } from "../environments/api";
import {
  createManualLibraryMapping,
  createManualMapping,
  discoverSoundCloudTrack,
  listManualLibraryTrackCandidates,
  listManualFileCandidates,
  listMatchReview,
  matchDownloads,
  playbackAudioUrl,
  runLibraryMatching,
  runMatching,
  syncMissingSoundCloudSources,
} from "./api";

type ReviewFilter =
  | "needs_review"
  | "all"
  | "matched"
  | "missing_audio"
  | "ambiguous"
  | "manually_mapped"
  | "library_needs_review"
  | "library_matched"
  | "missing_library"
  | "ambiguous_library"
  | "manually_mapped_library";

type PreviewState = {
  audioFileId: string;
  label: string;
  detail: string;
  url: string;
};

export function MatchingPanel() {
  const { selectedEnvironmentId, openLibraryTrack } = useAppState();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const [rows, setRows] = useState<MatchReviewRow[]>([]);
  const [selectedEnvironment, setSelectedEnvironment] = useState<EnvironmentRead | null>(null);
  const [filter, setFilter] = useState<ReviewFilter>("needs_review");
  const [reviewSearch, setReviewSearch] = useState("");
  const [runSummary, setRunSummary] = useState<MatchingRunSummary | null>(null);
  const [libraryRunSummary, setLibraryRunSummary] = useState<LibraryMatchingRunSummary | null>(
    null,
  );
  const [downloadMatchResult, setDownloadMatchResult] =
    useState<DownloadMatchRunResultRead | null>(null);
  const [sourceSyncResult, setSourceSyncResult] =
    useState<SoundCloudSourceSyncResultRead | null>(null);
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [sourceDiscovery, setSourceDiscovery] = useState<SoundCloudTrackDiscoveryRead | null>(null);
  const [sourceDiscoverySongId, setSourceDiscoverySongId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isRunningLibrary, setIsRunningLibrary] = useState(false);
  const [isMatchingDownloads, setIsMatchingDownloads] = useState(false);
  const [isDiscoveringSource, setIsDiscoveringSource] = useState(false);
  const [isSyncingSources, setIsSyncingSources] = useState(false);
  const [mappingKey, setMappingKey] = useState<string | null>(null);
  const [libraryMappingKey, setLibraryMappingKey] = useState<string | null>(null);
  const [manualMatchRow, setManualMatchRow] = useState<MatchReviewRow | null>(null);
  const [manualCandidateQuery, setManualCandidateQuery] = useState("");
  const [manualCandidates, setManualCandidates] = useState<MatchCandidateRead[]>([]);
  const [isSearchingManualCandidates, setIsSearchingManualCandidates] = useState(false);
  const [manualLibraryMatchRow, setManualLibraryMatchRow] = useState<MatchReviewRow | null>(null);
  const [manualLibraryCandidateQuery, setManualLibraryCandidateQuery] = useState("");
  const [manualLibraryCandidates, setManualLibraryCandidates] = useState<
    LibraryTrackCandidateRead[]
  >([]);
  const [isSearchingManualLibraryCandidates, setIsSearchingManualLibraryCandidates] =
    useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playbackError, setPlaybackError] = useState<string | null>(null);

  const refreshReview = useCallback(
    async (environmentId: string) => {
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
    },
    [],
  );

  useEffect(() => {
    if (!selectedEnvironmentId) {
      setRows([]);
      setSelectedEnvironment(null);
      setRunSummary(null);
      setLibraryRunSummary(null);
      setDownloadMatchResult(null);
      setSourceSyncResult(null);
      setPreview(null);
      setSourceDiscovery(null);
      setSourceDiscoverySongId(null);
      setManualMatchRow(null);
      setManualCandidates([]);
      setManualCandidateQuery("");
      setManualLibraryMatchRow(null);
      setManualLibraryCandidates([]);
      setManualLibraryCandidateQuery("");
      return;
    }
    void refreshReview(selectedEnvironmentId);
    void listEnvironments()
      .then((environments) => {
        setSelectedEnvironment(
          environments.find((environment) => environment.id === selectedEnvironmentId) ?? null,
        );
      })
      .catch(() => {
        setSelectedEnvironment(null);
      });
  }, [refreshReview, selectedEnvironmentId]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !preview) {
      return;
    }
    setPlaybackError(null);
    void audio.play().catch((playError: unknown) => {
      setPlaybackError(errorMessage(playError));
      setIsPlaying(false);
    });
  }, [preview]);

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
        if (!isRunning && !isRunningLibrary && selectedEnvironmentId) {
          void handleRunMatching();
        }
        return;
      }
      if (event.key === "Escape") {
        setReviewSearch("");
        setPreview(null);
        setPlaybackError(null);
        audioRef.current?.pause();
        return;
      }
      const shortcutFilters: ReviewFilter[] = [
        "needs_review",
        "all",
        "matched",
        "missing_audio",
        "ambiguous",
      ];
      const shortcutIndex = Number(event.key) - 1;
      if (shortcutIndex >= 0 && shortcutIndex < shortcutFilters.length) {
        event.preventDefault();
        setFilter(shortcutFilters[shortcutIndex]);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isRunning, isRunningLibrary, selectedEnvironmentId]);

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
          row.candidates.some((candidate) =>
            [
              candidate.path,
              candidate.title ?? "",
              candidate.artist ?? "",
              candidate.method,
            ].some((value) => value.toLowerCase().includes(query)),
          ) ||
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
        if (filter === "all") {
          return matchesText;
        }
        if (filter === "needs_review") {
          return matchesText && (row.status === "missing_audio" || row.status === "ambiguous");
        }
        if (filter === "library_needs_review") {
          return (
            matchesText &&
            (row.library_status === "missing_library" ||
              row.library_status === "ambiguous_library")
          );
        }
        if (
          filter === "library_matched" ||
          filter === "missing_library" ||
          filter === "ambiguous_library" ||
          filter === "manually_mapped_library"
        ) {
          return matchesText && row.library_status === filter;
        }
        return matchesText && row.status === filter;
      }),
    [filter, reviewSearch, rows],
  );

  async function handleRunMatching() {
    if (!selectedEnvironmentId) {
      setError("Select an environment before running matching.");
      return;
    }
    setIsRunning(true);
    setError(null);
    try {
      const summary = await runMatching(selectedEnvironmentId);
      setRunSummary(summary);
      setLibraryRunSummary(null);
      setDownloadMatchResult(null);
      setSourceSyncResult(null);
      await refreshReview(selectedEnvironmentId);
    } catch (runError) {
      setError(errorMessage(runError));
    } finally {
      setIsRunning(false);
    }
  }

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
      setRunSummary(null);
      setDownloadMatchResult(null);
      setSourceSyncResult(null);
      await refreshReview(selectedEnvironmentId);
    } catch (runError) {
      setError(errorMessage(runError));
    } finally {
      setIsRunningLibrary(false);
    }
  }

  async function handleMatchDownloads() {
    if (!selectedEnvironmentId) {
      setError("Select an environment before matching downloads.");
      return;
    }
    if (!selectedEnvironment?.download_path) {
      setError("Configure a download folder before matching downloads.");
      return;
    }
    setIsMatchingDownloads(true);
    setError(null);
    try {
      const result = await matchDownloads(selectedEnvironmentId);
      setDownloadMatchResult(result);
      setRunSummary(null);
      setLibraryRunSummary(null);
      setSourceSyncResult(null);
      await refreshReview(selectedEnvironmentId);
    } catch (matchError) {
      setError(errorMessage(matchError));
    } finally {
      setIsMatchingDownloads(false);
    }
  }

  async function handleMapCandidate(row: MatchReviewRow, candidate: MatchCandidateRead) {
    if (!selectedEnvironmentId) {
      return;
    }
    const key = `${row.song_id}-${candidate.audio_file_id}`;
    setMappingKey(key);
    setError(null);
    try {
      await createManualMapping(selectedEnvironmentId, {
        song_id: row.song_id,
        audio_file_id: candidate.audio_file_id,
      });
      await refreshReview(selectedEnvironmentId);
      if (manualMatchRow?.song_id === row.song_id) {
        setManualMatchRow(null);
        setManualCandidates([]);
        setManualCandidateQuery("");
      }
    } catch (mappingError) {
      setError(errorMessage(mappingError));
    } finally {
      setMappingKey(null);
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

  async function openManualMatchModal(row: MatchReviewRow) {
    if (!selectedEnvironmentId) {
      return;
    }
    const initialQuery = [row.title, row.artist].filter(Boolean).join(" ");
    setManualMatchRow(row);
    setManualCandidateQuery(initialQuery);
    setManualCandidates([]);
    await loadManualCandidates(row, initialQuery);
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

  async function loadManualCandidates(row: MatchReviewRow, query: string) {
    if (!selectedEnvironmentId) {
      return;
    }
    setIsSearchingManualCandidates(true);
    setError(null);
    try {
      setManualCandidates(
        await listManualFileCandidates(selectedEnvironmentId, row.song_id, query),
      );
    } catch (candidateError) {
      setManualCandidates([]);
      setError(errorMessage(candidateError));
    } finally {
      setIsSearchingManualCandidates(false);
    }
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

  async function handleManualCandidateSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (manualMatchRow) {
      await loadManualCandidates(manualMatchRow, manualCandidateQuery);
    }
  }

  async function handleManualLibraryCandidateSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (manualLibraryMatchRow) {
      await loadManualLibraryCandidates(manualLibraryMatchRow, manualLibraryCandidateQuery);
    }
  }

  function handlePreviewAudio(audioFileId: string, label: string, detail: string) {
    if (!selectedEnvironmentId) {
      return;
    }
    const currentAudio = audioRef.current;
    if (preview?.audioFileId === audioFileId && currentAudio && !currentAudio.paused) {
      currentAudio.pause();
      return;
    }
    setPreview({
      audioFileId,
      label,
      detail,
      url: playbackAudioUrl(selectedEnvironmentId, audioFileId),
    });
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
      setDownloadMatchResult(null);
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
          <span className="top-tabs__active">Matching Review</span>
        </div>
        <div className="top-actions">
          <button className="icon-button" disabled type="button" title="Folder picker arrives in a later wave">
            <Search size={17} />
          </button>
          <button
            className="icon-button"
            disabled={isRunning || !selectedEnvironmentId}
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
            description="Create or select an environment, import playlists, and scan audio before reviewing matches."
          />
        </Panel>
      ) : (
        <main className="matching-main">
          <section className="matching-header">
            <div>
              <h2>Matching Review</h2>
              <p className="muted">Resolve track mismatches and map ambiguous candidates.</p>
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
                disabled={
                  isMatchingDownloads || !selectedEnvironmentId || !selectedEnvironment?.download_path
                }
                icon={<Download size={18} />}
                onClick={handleMatchDownloads}
              >
                {isMatchingDownloads ? "Matching Downloads" : "Match Downloads"}
              </Button>
              <Button
                disabled={isRunning}
                icon={<Zap size={18} />}
                variant="primary"
                onClick={handleRunMatching}
              >
                {isRunning ? "Running" : "Run Matching"}
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

          {runSummary ? <RunSummary summary={runSummary} /> : null}
          {libraryRunSummary ? <LibraryRunSummary summary={libraryRunSummary} /> : null}
          {downloadMatchResult ? <DownloadMatchSummary result={downloadMatchResult} /> : null}
          {sourceSyncResult ? <SourceSyncSummary result={sourceSyncResult} /> : null}

          <ReviewFilters counts={counts} filter={filter} onFilterChange={setFilter} />

          {sourceDiscovery ? (
            <SourceDiscoveryPanel
              discovery={sourceDiscovery}
              onClose={() => {
                setSourceDiscovery(null);
                setSourceDiscoverySongId(null);
              }}
            />
          ) : null}

          <label className="matching-search-field">
            <Search size={15} />
            <input
              ref={searchInputRef}
              aria-label="Search matching review"
              placeholder="Search title, artist, candidate path, or method... (/)"
              value={reviewSearch}
              onChange={(event) => setReviewSearch(event.target.value)}
            />
          </label>

          {isLoading ? <LoadingState label="Loading review rows" /> : null}

          {!isLoading && rows.length === 0 ? (
            <Panel className="matching-empty-panel">
              <EmptyState
                title="No imported songs to review"
                description="Import a SoundCloud playlist, scan local audio, then run matching to populate review rows."
              />
            </Panel>
          ) : null}

          {filteredRows.length > 0 ? (
            <section className="matching-table" aria-label="Matching review rows">
              <div className="matching-table-header">
                <span>Target Track</span>
                <span>Duration</span>
                <span>Status</span>
                <span>Actions</span>
              </div>
              <div className="matching-review-list">
                {filteredRows.map((row) => (
                  <ReviewRow
                    key={row.song_id}
                    mappingKey={mappingKey}
                    libraryMappingKey={libraryMappingKey}
                    row={row}
                    isDiscoveringSource={
                      isDiscoveringSource && sourceDiscoverySongId === row.song_id
                    }
                    onMapCandidate={handleMapCandidate}
                    onMapLibraryCandidate={handleMapLibraryCandidate}
                    onDiscoverSource={handleDiscoverSource}
                    onOpenLibraryTrack={openLibraryTrack}
                    onOpenManualLibraryMatch={openManualLibraryMatchModal}
                    onOpenManualMatch={openManualMatchModal}
                    onPreviewAudio={handlePreviewAudio}
                  />
                ))}
              </div>
            </section>
          ) : rows.length > 0 ? (
            <Panel className="matching-empty-panel">
              <EmptyState
                title="No rows in this filter"
                description="Choose another filter or run matching again after scanning/importing more audio."
              />
            </Panel>
          ) : null}
        </main>
      )}

      <ManualMatchModal
        candidates={manualCandidates}
        isMapping={mappingKey}
        isSearching={isSearchingManualCandidates}
        query={manualCandidateQuery}
        row={manualMatchRow}
        onClose={() => {
          setManualMatchRow(null);
          setManualCandidates([]);
          setManualCandidateQuery("");
        }}
        onMapCandidate={handleMapCandidate}
        onPreviewAudio={handlePreviewAudio}
        onQueryChange={setManualCandidateQuery}
        onSearch={handleManualCandidateSearch}
      />

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

      <MiniPreviewPlayer
        audioRef={audioRef}
        isPlaying={isPlaying}
        playbackError={playbackError}
        preview={preview}
        onPause={() => setIsPlaying(false)}
        onPlay={() => setIsPlaying(true)}
        onPlaybackError={() => {
          setPlaybackError("Playback failed. The local file may be unavailable or unreadable.");
          setIsPlaying(false);
        }}
      />
    </div>
  );
}

type ReviewFiltersProps = {
  counts: Record<ReviewFilter, number>;
  filter: ReviewFilter;
  onFilterChange: (filter: ReviewFilter) => void;
};

function ReviewFilters({ counts, filter, onFilterChange }: ReviewFiltersProps) {
  const items: Array<{ filter: ReviewFilter; label: string; tone?: string }> = [
    { filter: "needs_review", label: "Needs Review", tone: "warning" },
    { filter: "all", label: "All" },
    { filter: "matched", label: "Matched", tone: "success" },
    { filter: "missing_audio", label: "Missing", tone: "danger" },
    { filter: "ambiguous", label: "Ambiguous", tone: "warning" },
    { filter: "manually_mapped", label: "Manual", tone: "accent" },
    { filter: "library_needs_review", label: "Library Review", tone: "warning" },
    { filter: "library_matched", label: "Library Matched", tone: "success" },
    { filter: "missing_library", label: "Library Missing", tone: "danger" },
    { filter: "ambiguous_library", label: "Library Ambiguous", tone: "warning" },
    { filter: "manually_mapped_library", label: "Library Manual", tone: "accent" },
  ];

  return (
    <div className="matching-filter-row" aria-label="Review filters">
      {items.map((item) => (
        <button
          className={[
            "matching-filter",
            item.tone ? `matching-filter--${item.tone}` : "",
            filter === item.filter ? "is-active" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          key={item.filter}
          type="button"
          onClick={() => onFilterChange(item.filter)}
        >
          {item.tone ? <span aria-hidden="true" /> : null}
          {item.label} ({formatNumber(counts[item.filter])})
        </button>
      ))}
    </div>
  );
}

function RunSummary({ summary }: { summary: MatchingRunSummary }) {
  return (
    <div className="matching-run-summary">
      <StatusBadge tone="success">Matching Complete</StatusBadge>
      <span>{formatNumber(summary.total)} songs reviewed</span>
      <span>{formatNumber(summary.matched)} matched</span>
      <span>{formatNumber(summary.missing_audio)} missing</span>
      <span>{formatNumber(summary.ambiguous)} ambiguous</span>
      <span>{formatNumber(summary.manually_mapped)} manual</span>
    </div>
  );
}

function LibraryRunSummary({ summary }: { summary: LibraryMatchingRunSummary }) {
  return (
    <div className="matching-run-summary">
      <StatusBadge tone={summary.ambiguous_library > 0 ? "warning" : "success"}>
        Library Matching Complete
      </StatusBadge>
      <span>{formatNumber(summary.total)} songs reviewed</span>
      <span>{formatNumber(summary.matched)} library matched</span>
      <span>{formatNumber(summary.missing_library)} missing</span>
      <span>{formatNumber(summary.ambiguous_library)} ambiguous</span>
      <span>{formatNumber(summary.manually_mapped_library)} manual</span>
    </div>
  );
}

function DownloadMatchSummary({ result }: { result: DownloadMatchRunResultRead }) {
  return (
    <div className="matching-run-summary">
      <StatusBadge tone="success">Downloads Matched</StatusBadge>
      <span>{formatNumber(result.scan.added)} new files</span>
      <span>{formatNumber(result.scan.changed + result.scan.moved)} changed or moved</span>
      <span>{formatNumber(result.matching.checked)} songs checked</span>
      <span>{formatNumber(result.matching.matched)} matched</span>
      <span>{formatNumber(result.matching.ambiguous)} ambiguous</span>
      <span>{formatNumber(result.matching.preserved_reviewed)} preserved</span>
    </div>
  );
}

function SourceSyncSummary({ result }: { result: SoundCloudSourceSyncResultRead }) {
  return (
    <div className="matching-run-summary">
      <StatusBadge tone={result.failed > 0 ? "warning" : "success"}>
        {result.failed > 0 ? "Source Sync Issues" : "Sources Synced"}
      </StatusBadge>
      <span>{formatNumber(result.total)} unmatched songs checked</span>
      <span>{formatNumber(result.discovered)} discovered</span>
      <span>{formatNumber(result.skipped)} already known</span>
      <span>{formatNumber(result.failed)} failed</span>
    </div>
  );
}

function SourceDiscoveryPanel({
  discovery,
  onClose,
}: {
  discovery: SoundCloudTrackDiscoveryRead;
  onClose: () => void;
}) {
  const primaryLinks = discovery.links.filter((link) =>
    ["buy", "download", "buy_or_download"].includes(link.kind),
  );
  const secondaryLinks = discovery.links.filter(
    (link) => !["buy", "download", "buy_or_download"].includes(link.kind),
  );
  const links = [...primaryLinks, ...secondaryLinks];

  return (
    <section className="source-discovery-panel">
      <header>
        <div>
          <p className="eyebrow">SoundCloud Source Discovery</p>
          <h3>{discovery.title}</h3>
          <span>{discovery.artist ?? "Unknown uploader"}</span>
        </div>
        <button className="icon-button" type="button" onClick={onClose} title="Close source discovery">
          <X size={16} />
        </button>
      </header>

      <div className="source-discovery-actions">
        <a href={discovery.track_url} rel="noreferrer" target="_blank">
          <ExternalLink size={15} />
          Open SoundCloud track
        </a>
        {discovery.purchase_url ? (
          <a href={discovery.purchase_url} rel="noreferrer" target="_blank">
            <ShoppingCart size={15} />
            {discovery.purchase_title ?? "Buy / Download"}
          </a>
        ) : null}
      </div>

      {discovery.warnings.length > 0 ? (
        <div className="source-discovery-warnings">
          <AlertTriangle size={15} />
          <span>{discovery.warnings.map(sourceWarningLabel).join(" ")}</span>
        </div>
      ) : null}

      {links.length > 0 ? (
        <div className="source-link-list">
          {links.map((link) => (
            <a href={link.url} key={`${link.source}-${link.url}`} rel="noreferrer" target="_blank">
              <span>{link.label || link.url}</span>
              <em>{sourceLinkKindLabel(link.kind)} · {sourceLabel(link.source)}</em>
              <ExternalLink size={14} />
            </a>
          ))}
        </div>
      ) : (
        <p className="muted">No buy, download, or artist source links were exposed for this track.</p>
      )}

      {discovery.description ? (
        <details className="source-description">
          <summary>Description</summary>
          <p>{linkifyText(discovery.description)}</p>
        </details>
      ) : null}
    </section>
  );
}

type ReviewRowProps = {
  row: MatchReviewRow;
  mappingKey: string | null;
  libraryMappingKey: string | null;
  isDiscoveringSource: boolean;
  onDiscoverSource: (row: MatchReviewRow) => void;
  onMapCandidate: (row: MatchReviewRow, candidate: MatchCandidateRead) => void;
  onMapLibraryCandidate: (row: MatchReviewRow, candidate: LibraryTrackCandidateRead) => void;
  onOpenManualLibraryMatch: (row: MatchReviewRow) => void;
  onOpenManualMatch: (row: MatchReviewRow) => void;
  onOpenLibraryTrack: (libraryTrackId: string) => void;
  onPreviewAudio: (audioFileId: string, label: string, detail: string) => void;
};

function ReviewRow({
  row,
  mappingKey,
  libraryMappingKey,
  isDiscoveringSource,
  onDiscoverSource,
  onMapCandidate,
  onMapLibraryCandidate,
  onOpenLibraryTrack,
  onOpenManualLibraryMatch,
  onOpenManualMatch,
  onPreviewAudio,
}: ReviewRowProps) {
  const expanded =
    row.status === "ambiguous" ||
    row.candidates.length > 0 ||
    row.library_status === "ambiguous_library" ||
    row.library_candidates.length > 0;
  const acceptedMatch = row.match;
  const acceptedLibraryMatch = row.library_match;
  const sourceLink = bestSourceLink(row.source_discovery);
  return (
    <article className={["matching-row", `matching-row--${row.status}`].join(" ")}>
      <div className="matching-row-main">
        <div className="matching-row-title">
          <StatusIcon status={row.status} />
          <div>
            <strong>{row.title}</strong>
            <span>{row.artist ?? "Unknown artist"}</span>
          </div>
        </div>
        <span className="matching-row-duration">{formatDuration(row.duration_seconds)}</span>
        <div className="matching-status-stack">
          <MatchStatusPill status={row.status} />
          {row.library_status ? <LibraryMatchStatusPill status={row.library_status} /> : null}
        </div>
        <div className="matching-row-actions">
          {!acceptedLibraryMatch && row.library_status ? (
            <Button
              icon={<Library size={15} />}
              type="button"
              onClick={() => onOpenManualLibraryMatch(row)}
            >
              Map Library Track
            </Button>
          ) : null}
          {acceptedMatch ? (
            <button
              className="icon-button"
              title="Preview accepted audio"
              type="button"
              onClick={() =>
                onPreviewAudio(
                  acceptedMatch.audio_file_id,
                  acceptedMatch.title ?? row.title,
                  acceptedMatch.path,
                )
              }
            >
              <Play size={16} />
            </button>
          ) : (
            <>
              <Button
                icon={<Link2 size={15} />}
                type="button"
                onClick={() => onOpenManualMatch(row)}
              >
                Map Local File
              </Button>
              {sourceLink ? (
                <a
                  className="button button--ghost source-action-link"
                  href={sourceLink.url}
                  rel="noreferrer"
                  target="_blank"
                >
                  <ShoppingCart size={15} />
                  {sourceLink.label}
                </a>
              ) : row.source_discovery ? (
                <a
                  className="button button--ghost source-action-link"
                  href={row.source_discovery.track_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  <ExternalLink size={15} />
                  Open Track
                </a>
              ) : (
                <Button
                  disabled={isDiscoveringSource}
                  icon={<ShoppingCart size={15} />}
                  type="button"
                  onClick={() => onDiscoverSource(row)}
                >
                  {isDiscoveringSource ? "Finding" : "Find Source"}
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {!acceptedMatch && row.source_discovery?.description ? (
        <details className="matching-source-description">
          <summary>Source description</summary>
          <p>{linkifyText(row.source_discovery.description)}</p>
        </details>
      ) : null}

      {acceptedMatch ? (
        <div className="accepted-match-row">
          <CheckCircle2 size={15} />
          <span>{acceptedMatch.path}</span>
          <em>
            {sourceAreaLabel(acceptedMatch.source_area)} - {confidenceLabel(acceptedMatch.confidence)} via{" "}
            {methodLabel(acceptedMatch.method)}
          </em>
          {hasLikelyPreviewWarning(acceptedMatch) ? (
            <strong className="accepted-match-warning">
              Likely preview download. Unmatch this audio and move it to deprecated before exporting.
            </strong>
          ) : null}
        </div>
      ) : null}

      {acceptedLibraryMatch ? (
        <div className="accepted-match-row accepted-library-row">
          <Library size={15} />
          <span>{acceptedLibraryMatch.path}</span>
          <em>
            Library - {confidenceLabel(acceptedLibraryMatch.confidence)} via{" "}
            {methodLabel(acceptedLibraryMatch.method)}
          </em>
          <button
            className="icon-button"
            type="button"
            title="Open in Library"
            onClick={() => onOpenLibraryTrack(acceptedLibraryMatch.library_track_id)}
          >
            <ExternalLink size={15} />
          </button>
        </div>
      ) : null}

      {expanded ? (
        <div className="candidate-list">
          <div className="candidate-list-title">Candidates found in collection</div>
          {row.candidates.length > 0 ? (
            row.candidates.map((candidate) => (
              <CandidateCard
                candidate={candidate}
                isMapping={mappingKey === `${row.song_id}-${candidate.audio_file_id}`}
                key={candidate.audio_file_id}
                row={row}
                onMapCandidate={onMapCandidate}
                onPreviewAudio={onPreviewAudio}
              />
            ))
          ) : (
            <div className="candidate-empty">
              <AlertTriangle size={15} />
              <span>No viable local audio candidates were found.</span>
            </div>
          )}
          {row.library_status === "ambiguous_library" || row.library_candidates.length > 0 ? (
            <>
              <div className="candidate-list-title">Library candidates</div>
              {row.library_candidates.length > 0 ? (
                row.library_candidates.map((candidate) => (
                  <LibraryCandidateCard
                    candidate={candidate}
                    isMapping={
                      libraryMappingKey === `${row.song_id}-${candidate.library_track_id}`
                    }
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
            </>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

type CandidateCardProps = {
  candidate: MatchCandidateRead;
  row: MatchReviewRow;
  isMapping: boolean;
  onMapCandidate: (row: MatchReviewRow, candidate: MatchCandidateRead) => void;
  onPreviewAudio: (audioFileId: string, label: string, detail: string) => void;
};

function CandidateCard({
  candidate,
  row,
  isMapping,
  onMapCandidate,
  onPreviewAudio,
}: CandidateCardProps) {
  const likelyPreview = hasLikelyPreviewWarning(candidate);
  return (
    <div className={["candidate-card", likelyPreview ? "candidate-card--warning" : ""].join(" ")}>
      <button
        className="candidate-play"
        title="Preview candidate"
        type="button"
        onClick={() =>
          onPreviewAudio(
            candidate.audio_file_id,
            candidate.title ?? row.title,
            candidate.path,
          )
        }
      >
        <Play size={16} />
      </button>
      <div className="candidate-body">
        <strong>{candidate.path}</strong>
        <span>
          {candidate.title ?? "Unknown title"}
          {candidate.artist ? ` · ${candidate.artist}` : ""}
        </span>
        <div>
          <em>{confidenceLabel(candidate.confidence)} match</em>
          <span>{sourceAreaLabel(candidate.source_area)}</span>
          <span>{methodLabel(candidate.method)}</span>
          <span>{formatDuration(candidate.duration_seconds)}</span>
        </div>
        {likelyPreview ? (
          <p className="candidate-warning">
            Likely preview download. Consider unmatching and moving this file to deprecated.
          </p>
        ) : null}
      </div>
      <Button
        disabled={isMapping}
        icon={<Link2 size={15} />}
        onClick={() => onMapCandidate(row, candidate)}
      >
        {isMapping ? "Mapping" : "Map File"}
      </Button>
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
          {candidate.artist ? ` · ${candidate.artist}` : ""}
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

type ManualMatchModalProps = {
  candidates: MatchCandidateRead[];
  isMapping: string | null;
  isSearching: boolean;
  query: string;
  row: MatchReviewRow | null;
  onClose: () => void;
  onMapCandidate: (row: MatchReviewRow, candidate: MatchCandidateRead) => void;
  onPreviewAudio: (audioFileId: string, label: string, detail: string) => void;
  onQueryChange: (query: string) => void;
  onSearch: (event: FormEvent<HTMLFormElement>) => void;
};

function ManualMatchModal({
  candidates,
  isMapping,
  isSearching,
  query,
  row,
  onClose,
  onMapCandidate,
  onPreviewAudio,
  onQueryChange,
  onSearch,
}: ManualMatchModalProps) {
  if (!row) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <div
        className="usb-match-dialog manual-match-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="manual-match-title"
      >
        <header>
          <div>
            <p className="eyebrow">Map local file</p>
            <h2 id="manual-match-title">{row.title}</h2>
            <p className="muted">
              {row.artist ?? "Unknown artist"} · {formatDuration(row.duration_seconds)}
            </p>
          </div>
          <MatchStatusPill status={row.status} />
        </header>

        <form className="usb-match-search" onSubmit={onSearch}>
          <label className="playlist-search-field playlist-search-field--wide">
            <Search size={14} />
            <input
              aria-label="Search local audio files"
              placeholder="Search USB and download files..."
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
            />
          </label>
          <Button disabled={isSearching} type="submit">
            {isSearching ? "Searching" : "Search"}
          </Button>
        </form>

        <div className="usb-candidate-list manual-file-candidate-list">
          {isSearching ? <LoadingState label="Searching local files" /> : null}
          {!isSearching && candidates.length === 0 ? (
            <EmptyState
              title="No local files found"
              description="No active unmapped USB or download files match this search."
            />
          ) : null}
          {candidates.map((candidate) => (
            <CandidateCard
              candidate={candidate}
              isMapping={isMapping === `${row.song_id}-${candidate.audio_file_id}`}
              key={candidate.audio_file_id}
              row={row}
              onMapCandidate={onMapCandidate}
              onPreviewAudio={onPreviewAudio}
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
              {row.artist ?? "Unknown artist"} · {formatDuration(row.duration_seconds)}
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

function MiniPreviewPlayer({
  audioRef,
  isPlaying,
  playbackError,
  preview,
  onPause,
  onPlay,
  onPlaybackError,
}: {
  audioRef: RefObject<HTMLAudioElement>;
  isPlaying: boolean;
  playbackError: string | null;
  preview: PreviewState | null;
  onPause: () => void;
  onPlay: () => void;
  onPlaybackError: () => void;
}) {
  return (
    <footer className="mini-preview-player">
      <audio
        ref={audioRef}
        src={preview?.url}
        onEnded={onPause}
        onError={onPlaybackError}
        onPause={onPause}
        onPlay={onPlay}
      />
      <div className="mini-preview-track">
        <div className="mini-preview-art">
          <Play size={18} />
        </div>
        <div>
          <strong>{preview?.label ?? "No preview selected"}</strong>
          <span>{playbackError ?? preview?.detail ?? "Select a candidate or accepted match to preview."}</span>
        </div>
      </div>
      <button
        className="mini-preview-play"
        disabled={!preview}
        type="button"
        onClick={() => {
          const audio = audioRef.current;
          if (!audio) {
            return;
          }
          if (audio.paused) {
            void audio.play().catch(onPlaybackError);
          } else {
            audio.pause();
          }
        }}
      >
        {isPlaying ? "Pause" : "Play"}
      </button>
    </footer>
  );
}

function StatusIcon({ status }: { status: MatchStatus }) {
  if (status === "matched" || status === "manually_mapped") {
    return <CheckCircle2 size={19} />;
  }
  if (status === "ambiguous") {
    return <CircleHelp size={19} />;
  }
  return <AlertTriangle size={19} />;
}

function MatchStatusPill({ status }: { status: MatchStatus }) {
  return <span className={`match-pill match-pill--${pillTone(status)}`}>{matchStatusLabel(status)}</span>;
}

function LibraryMatchStatusPill({ status }: { status: LibraryMatchStatus }) {
  return (
    <span className={`match-pill match-pill--${libraryPillTone(status)}`}>
      {libraryStatusLabel(status)}
    </span>
  );
}

function reviewCounts(rows: MatchReviewRow[]): Record<ReviewFilter, number> {
  const counts: Record<ReviewFilter, number> = {
    needs_review: 0,
    all: rows.length,
    matched: 0,
    missing_audio: 0,
    ambiguous: 0,
    manually_mapped: 0,
    library_needs_review: 0,
    library_matched: 0,
    missing_library: 0,
    ambiguous_library: 0,
    manually_mapped_library: 0,
  };
  for (const row of rows) {
    counts[row.status] += 1;
    if (row.status === "missing_audio" || row.status === "ambiguous") {
      counts.needs_review += 1;
    }
    if (row.library_status) {
      counts[row.library_status] += 1;
      if (row.library_status === "missing_library" || row.library_status === "ambiguous_library") {
        counts.library_needs_review += 1;
      }
    }
  }
  return counts;
}

function pillTone(status: MatchStatus) {
  if (status === "matched") {
    return "matched";
  }
  if (status === "missing_audio") {
    return "missing";
  }
  if (status === "ambiguous") {
    return "ambiguous";
  }
  return "manual";
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

function libraryPillTone(status: LibraryMatchStatus) {
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

function libraryStatusLabel(status: LibraryMatchStatus) {
  const labels: Record<LibraryMatchStatus, string> = {
    library_matched: "Library",
    missing_library: "No Library",
    ambiguous_library: "Library Ambiguous",
    manually_mapped_library: "Library Manual",
  };
  return labels[status];
}

function methodLabel(method: string) {
  return method.replace(/_/g, " ");
}

function sourceAreaLabel(sourceArea: MatchCandidateRead["source_area"]) {
  if (sourceArea === "download") {
    return "Downloads";
  }
  if (sourceArea === "usb") {
    return "USB";
  }
  return "Other";
}

function hasLikelyPreviewWarning(candidate: MatchCandidateRead) {
  return candidate.warnings.includes("likely_preview_download");
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

function sourceLabel(source: string) {
  return source.replace(/_/g, " ");
}

function sourceWarningLabel(warning: string) {
  const labels: Record<string, string> = {
    free_download_mentioned_without_link:
      "The description mentions a free download, but no public download link was exposed.",
    no_purchase_or_download_link_found:
      "No buy or download link was found.",
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
