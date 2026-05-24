import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  Link2,
  Play,
  RefreshCw,
  Search,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";

import { ApiError } from "../../shared/api/http";
import type {
  MatchCandidateRead,
  MatchingRunSummary,
  MatchReviewRow,
  MatchStatus,
} from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import { Button, EmptyState, ErrorBanner, LoadingState, Panel, StatusBadge } from "../../shared/ui";
import {
  createManualMapping,
  listMatchReview,
  playbackAudioUrl,
  runMatching,
} from "./api";

type ReviewFilter =
  | "needs_review"
  | "all"
  | "matched"
  | "missing_audio"
  | "ambiguous"
  | "manually_mapped";

type PreviewState = {
  audioFileId: string;
  label: string;
  detail: string;
  url: string;
};

export function MatchingPanel() {
  const { selectedEnvironmentId } = useAppState();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [rows, setRows] = useState<MatchReviewRow[]>([]);
  const [filter, setFilter] = useState<ReviewFilter>("needs_review");
  const [runSummary, setRunSummary] = useState<MatchingRunSummary | null>(null);
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [mappingKey, setMappingKey] = useState<string | null>(null);
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
      setRunSummary(null);
      setPreview(null);
      return;
    }
    void refreshReview(selectedEnvironmentId);
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

  const counts = useMemo(() => reviewCounts(rows), [rows]);
  const filteredRows = useMemo(
    () =>
      rows.filter((row) => {
        if (filter === "all") {
          return true;
        }
        if (filter === "needs_review") {
          return row.status === "missing_audio" || row.status === "ambiguous";
        }
        return row.status === filter;
      }),
    [filter, rows],
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
      await refreshReview(selectedEnvironmentId);
    } catch (runError) {
      setError(errorMessage(runError));
    } finally {
      setIsRunning(false);
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
    } catch (mappingError) {
      setError(errorMessage(mappingError));
    } finally {
      setMappingKey(null);
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
            <Button
              disabled={isRunning}
              icon={<Zap size={18} />}
              variant="primary"
              onClick={handleRunMatching}
            >
              {isRunning ? "Running" : "Run Matching"}
            </Button>
          </section>

          {runSummary ? <RunSummary summary={runSummary} /> : null}

          <ReviewFilters counts={counts} filter={filter} onFilterChange={setFilter} />

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
                    row={row}
                    onMapCandidate={handleMapCandidate}
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

type ReviewRowProps = {
  row: MatchReviewRow;
  mappingKey: string | null;
  onMapCandidate: (row: MatchReviewRow, candidate: MatchCandidateRead) => void;
  onPreviewAudio: (audioFileId: string, label: string, detail: string) => void;
};

function ReviewRow({ row, mappingKey, onMapCandidate, onPreviewAudio }: ReviewRowProps) {
  const expanded = row.status === "ambiguous" || row.candidates.length > 0;
  const acceptedMatch = row.match;
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
        <MatchStatusPill status={row.status} />
        <div className="matching-row-actions">
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
            <button className="icon-button" disabled title="No accepted audio" type="button">
              <Search size={16} />
            </button>
          )}
        </div>
      </div>

      {acceptedMatch ? (
        <div className="accepted-match-row">
          <CheckCircle2 size={15} />
          <span>{acceptedMatch.path}</span>
          <em>{confidenceLabel(acceptedMatch.confidence)} via {methodLabel(acceptedMatch.method)}</em>
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
  return (
    <div className="candidate-card">
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
          <span>{methodLabel(candidate.method)}</span>
          <span>{formatDuration(candidate.duration_seconds)}</span>
        </div>
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

function reviewCounts(rows: MatchReviewRow[]): Record<ReviewFilter, number> {
  const counts: Record<ReviewFilter, number> = {
    needs_review: 0,
    all: rows.length,
    matched: 0,
    missing_audio: 0,
    ambiguous: 0,
    manually_mapped: 0,
  };
  for (const row of rows) {
    counts[row.status] += 1;
    if (row.status === "missing_audio" || row.status === "ambiguous") {
      counts.needs_review += 1;
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

function methodLabel(method: string) {
  return method.replace(/_/g, " ");
}

function confidenceLabel(confidence: number) {
  return `${Math.round(confidence * 100)}%`;
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
