import {
  AlertTriangle,
  ArrowDownUp,
  CheckCircle2,
  Folder,
  FolderTree,
  Link2,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, RefObject } from "react";

import { ApiError } from "../../shared/api/http";
import type { UsbFileRead, UsbSongCandidateRead } from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import { Button, ConfirmDialog, EmptyState, ErrorBanner, LoadingState, Panel, StatusBadge } from "../../shared/ui";
import { createManualMapping } from "../matching/api";
import {
  listUsbFiles,
  listUsbMatchCandidates,
  playbackAudioUrl,
  quarantineUsbAudioFiles,
  quarantineUsbAudioFile,
} from "./api";

type UsbStatusFilter = "all" | "matched" | "unmatched" | "preview";
type UsbSortKey = "filename" | "duration" | "status" | "match";
type SortDirection = "asc" | "desc";

type FolderOption = {
  key: string;
  label: string;
  depth: number;
  count: number;
};

type PreviewState = {
  audioFileId: string;
  label: string;
  detail: string;
  url: string;
};

export function UsbFilesPanel() {
  const { selectedEnvironmentId } = useAppState();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [files, setFiles] = useState<UsbFileRead[]>([]);
  const [selectedFolderKey, setSelectedFolderKey] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<UsbStatusFilter>("all");
  const [sortKey, setSortKey] = useState<UsbSortKey>("filename");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [selectedFileIds, setSelectedFileIds] = useState<Set<string>>(() => new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matchFile, setMatchFile] = useState<UsbFileRead | null>(null);
  const [candidateQuery, setCandidateQuery] = useState("");
  const [candidates, setCandidates] = useState<UsbSongCandidateRead[]>([]);
  const [isSearchingCandidates, setIsSearchingCandidates] = useState(false);
  const [mappingSongId, setMappingSongId] = useState<string | null>(null);
  const [quarantineFile, setQuarantineFile] = useState<UsbFileRead | null>(null);
  const [bulkDeleteConfirmOpen, setBulkDeleteConfirmOpen] = useState(false);
  const [bulkDeleteConfirmation, setBulkDeleteConfirmation] = useState("");
  const [isQuarantining, setIsQuarantining] = useState(false);
  const [isBulkQuarantining, setIsBulkQuarantining] = useState(false);
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackError, setPlaybackError] = useState<string | null>(null);

  const refreshFiles = useCallback(
    async (environmentId: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const rows = await listUsbFiles(environmentId);
        setFiles(rows);
        setSelectedFileIds((current) => {
          const rowIds = new Set(rows.map((row) => row.audio_file_id));
          return new Set([...current].filter((audioFileId) => rowIds.has(audioFileId)));
        });
        setSelectedFolderKey((current) =>
          current === "" || rows.some((row) => folderKey(row.folder_parts).startsWith(current))
            ? current
            : "",
        );
      } catch (loadError) {
        setError(errorMessage(loadError));
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!selectedEnvironmentId) {
      setFiles([]);
      setSelectedFolderKey("");
      setMatchFile(null);
      setSelectedFileIds(new Set());
      setPreview(null);
      setPlaybackError(null);
      return;
    }
    void refreshFiles(selectedEnvironmentId);
  }, [refreshFiles, selectedEnvironmentId]);

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

  const folders = useMemo(() => buildFolderOptions(files), [files]);
  const counts = useMemo(() => usbCounts(files), [files]);
  const visibleFiles = useMemo(() => {
    const filteredFiles = files.filter((file) => {
      const query = search.trim().toLowerCase();
      const rowFolderKey = folderKey(file.folder_parts);
      const matchesFolder =
        selectedFolderKey === "" ||
        rowFolderKey === selectedFolderKey ||
        rowFolderKey.startsWith(`${selectedFolderKey}/`);
      const matchesSearch =
        query.length === 0 ||
        [
          file.filename,
          file.relative_path,
          file.title ?? "",
          file.artist ?? "",
          file.matched_song?.title ?? "",
          file.matched_song?.artist ?? "",
          ...(file.matched_song?.playlists ?? []),
        ].some((value) => value.toLowerCase().includes(query));
      const preview = isLikelyPreview(file);
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "preview"
          ? preview
          : statusFilter === "matched"
            ? file.match_status === "matched"
            : file.match_status === "unmatched");
      return matchesFolder && matchesSearch && matchesStatus;
    });
    return [...filteredFiles].sort((left, right) =>
      compareUsbFiles(left, right, sortKey, sortDirection),
    );
  }, [files, search, selectedFolderKey, sortDirection, sortKey, statusFilter]);

  const selectedCount = selectedFileIds.size;
  const allVisibleSelected =
    visibleFiles.length > 0 &&
    visibleFiles.every((file) => selectedFileIds.has(file.audio_file_id));

  async function openMatchModal(file: UsbFileRead) {
    if (!selectedEnvironmentId) {
      return;
    }
    const initialQuery = file.title ?? filenameStem(file.filename);
    setMatchFile(file);
    setCandidateQuery(initialQuery);
    await loadCandidates(file, initialQuery);
  }

  async function loadCandidates(file: UsbFileRead, query: string) {
    if (!selectedEnvironmentId) {
      return;
    }
    setIsSearchingCandidates(true);
    setError(null);
    try {
      setCandidates(await listUsbMatchCandidates(selectedEnvironmentId, file.audio_file_id, query));
    } catch (candidateError) {
      setCandidates([]);
      setError(errorMessage(candidateError));
    } finally {
      setIsSearchingCandidates(false);
    }
  }

  async function handleCandidateSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (matchFile) {
      await loadCandidates(matchFile, candidateQuery);
    }
  }

  async function handleMapCandidate(candidate: UsbSongCandidateRead) {
    if (!selectedEnvironmentId || !matchFile) {
      return;
    }
    setMappingSongId(candidate.song_id);
    setError(null);
    try {
      await createManualMapping(selectedEnvironmentId, {
        song_id: candidate.song_id,
        audio_file_id: matchFile.audio_file_id,
      });
      await refreshFiles(selectedEnvironmentId);
      setMatchFile(null);
      setCandidates([]);
    } catch (mappingError) {
      setError(errorMessage(mappingError));
    } finally {
      setMappingSongId(null);
    }
  }

  function handlePreviewAudio(file: UsbFileRead) {
    if (!selectedEnvironmentId) {
      return;
    }
    const currentAudio = audioRef.current;
    if (preview?.audioFileId === file.audio_file_id && currentAudio && !currentAudio.paused) {
      currentAudio.pause();
      return;
    }
    setPreview({
      audioFileId: file.audio_file_id,
      label: file.title ?? filenameStem(file.filename),
      detail: file.relative_path,
      url: playbackAudioUrl(selectedEnvironmentId, file.audio_file_id),
    });
  }

  function handleSort(nextSortKey: UsbSortKey) {
    if (nextSortKey === sortKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextSortKey);
    setSortDirection(nextSortKey === "duration" ? "desc" : "asc");
  }

  function handleToggleSelected(audioFileId: string) {
    setSelectedFileIds((current) => {
      const next = new Set(current);
      if (next.has(audioFileId)) {
        next.delete(audioFileId);
      } else {
        next.add(audioFileId);
      }
      return next;
    });
  }

  function handleToggleVisibleSelected() {
    setSelectedFileIds((current) => {
      const next = new Set(current);
      if (allVisibleSelected) {
        for (const file of visibleFiles) {
          next.delete(file.audio_file_id);
        }
      } else {
        for (const file of visibleFiles) {
          next.add(file.audio_file_id);
        }
      }
      return next;
    });
  }

  function closeBulkDeleteConfirm() {
    setBulkDeleteConfirmOpen(false);
    setBulkDeleteConfirmation("");
  }

  async function handleConfirmQuarantine() {
    if (!selectedEnvironmentId || !quarantineFile) {
      return;
    }
    setIsQuarantining(true);
    setError(null);
    try {
      await quarantineUsbAudioFile(selectedEnvironmentId, quarantineFile.audio_file_id);
      setFiles((current) =>
        current.filter((file) => file.audio_file_id !== quarantineFile.audio_file_id),
      );
      setSelectedFileIds((current) => {
        const next = new Set(current);
        next.delete(quarantineFile.audio_file_id);
        return next;
      });
      if (matchFile?.audio_file_id === quarantineFile.audio_file_id) {
        setMatchFile(null);
      }
      if (preview?.audioFileId === quarantineFile.audio_file_id) {
        audioRef.current?.pause();
        setPreview(null);
        setPlaybackError(null);
      }
      setQuarantineFile(null);
    } catch (quarantineError) {
      setError(errorMessage(quarantineError));
    } finally {
      setIsQuarantining(false);
    }
  }

  async function handleConfirmBulkQuarantine() {
    if (!selectedEnvironmentId || selectedFileIds.size === 0) {
      return;
    }
    const selectedIds = [...selectedFileIds];
    setIsBulkQuarantining(true);
    setError(null);
    try {
      await quarantineUsbAudioFiles(selectedEnvironmentId, {
        audio_file_ids: selectedIds,
        confirmation: bulkDeleteConfirmation,
      });
      const removedIds = new Set(selectedIds);
      setFiles((current) => current.filter((file) => !removedIds.has(file.audio_file_id)));
      if (matchFile && removedIds.has(matchFile.audio_file_id)) {
        setMatchFile(null);
      }
      if (preview && removedIds.has(preview.audioFileId)) {
        audioRef.current?.pause();
        setPreview(null);
        setPlaybackError(null);
      }
      setSelectedFileIds(new Set());
      closeBulkDeleteConfirm();
    } catch (bulkDeleteError) {
      setError(errorMessage(bulkDeleteError));
    } finally {
      setIsBulkQuarantining(false);
    }
  }

  return (
    <div className="usb-workspace">
      <header className="playlist-topbar">
        <div className="top-tabs" aria-label="USB file context">
          <span>Environment</span>
          <span className="top-tabs__active">USB Files</span>
        </div>
        <div className="top-actions">
          <button className="icon-button" disabled type="button" title="USB root is managed by the selected environment">
            <FolderTree size={17} />
          </button>
          <button
            className="icon-button"
            disabled={isLoading || !selectedEnvironmentId}
            type="button"
            title="Refresh USB files"
            onClick={() => {
              if (selectedEnvironmentId) {
                void refreshFiles(selectedEnvironmentId);
              }
            }}
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      {error ? (
        <ErrorBanner
          title="USB files error"
          message={error}
          actionLabel={selectedEnvironmentId ? "Retry" : undefined}
          onAction={selectedEnvironmentId ? () => void refreshFiles(selectedEnvironmentId) : undefined}
        />
      ) : null}

      {!selectedEnvironmentId ? (
        <Panel className="playlist-empty-panel">
          <EmptyState
            title="Select an environment first"
            description="Choose a USB environment from the dashboard before reviewing scanned files."
          />
        </Panel>
      ) : (
        <div className="usb-browser">
          <aside className="usb-folder-panel">
            <div className="playlist-sidebar-header">
              <span>USB Folders</span>
            </div>
            {isLoading ? <LoadingState label="Loading USB files" /> : null}
            <div className="usb-folder-list">
              {folders.map((folder) => (
                <button
                  className={[
                    "usb-folder-item",
                    selectedFolderKey === folder.key ? "is-selected" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  key={folder.key}
                  style={{ paddingLeft: `${12 + folder.depth * 14}px` }}
                  type="button"
                  onClick={() => setSelectedFolderKey(folder.key)}
                >
                  <Folder size={15} />
                  <span>{folder.label}</span>
                  <em>{folder.count}</em>
                </button>
              ))}
            </div>
          </aside>

          <main className="usb-main">
            <section className="usb-header">
              <div>
                <p className="export-kicker">
                  <ShieldAlert size={17} />
                  USB File Audit
                </p>
                <h2>Scanned Audio Files</h2>
                <p>
                  Review unmatched files, isolate short preview downloads, and map useful loose files back to imported SoundCloud songs.
                </p>
              </div>
              <div className="playlist-chip-row">
                <button
                  className={[
                    "playlist-chip",
                    "playlist-chip--neutral",
                    statusFilter === "all" ? "is-active" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  type="button"
                  onClick={() => setStatusFilter("all")}
                >
                  {formatNumber(counts.total)} Files
                </button>
                <button
                  className={[
                    "playlist-chip",
                    "playlist-chip--success",
                    statusFilter === "matched" ? "is-active" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  type="button"
                  onClick={() => setStatusFilter("matched")}
                >
                  {formatNumber(counts.matched)} Matched
                </button>
                <button
                  className={[
                    "playlist-chip",
                    "playlist-chip--danger",
                    statusFilter === "unmatched" ? "is-active" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  type="button"
                  onClick={() => setStatusFilter("unmatched")}
                >
                  {formatNumber(counts.unmatched)} Unmatched
                </button>
                <button
                  className={[
                    "playlist-chip",
                    "playlist-chip--warning",
                    statusFilter === "preview" ? "is-active" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  type="button"
                  onClick={() => setStatusFilter("preview")}
                >
                  {formatNumber(counts.preview)} Preview risk
                </button>
              </div>
            </section>

            <div className="playlist-detail-tools">
              <label className="playlist-search-field playlist-search-field--wide">
                <Search size={14} />
                <input
                  aria-label="Search USB files"
                  placeholder="Search filename, metadata, playlist, or matched song..."
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
              </label>
              <select
                aria-label="Filter USB files by status"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as UsbStatusFilter)}
              >
                <option value="all">All files</option>
                <option value="unmatched">Unmatched</option>
                <option value="matched">Matched</option>
                <option value="preview">Likely previews</option>
              </select>
              <span>{formatNumber(visibleFiles.length)} visible</span>
              {selectedCount > 0 ? (
                <>
                  <span>{formatNumber(selectedCount)} selected</span>
                  <Button
                    icon={<Trash2 size={14} />}
                    variant="danger"
                    onClick={() => setBulkDeleteConfirmOpen(true)}
                  >
                    Delete Selected
                  </Button>
                </>
              ) : null}
            </div>

            <div className="playlist-table-wrap">
              <table className="playlist-table usb-table">
                <thead>
                  <tr>
                    <th className="selection-cell">
                      <input
                        aria-label="Select visible USB files"
                        checked={allVisibleSelected}
                        disabled={visibleFiles.length === 0}
                        type="checkbox"
                        onChange={handleToggleVisibleSelected}
                      />
                    </th>
                    <th>
                      <SortHeader
                        active={sortKey === "filename"}
                        direction={sortDirection}
                        label="File"
                        onClick={() => handleSort("filename")}
                      />
                    </th>
                    <th>
                      <SortHeader
                        active={sortKey === "duration"}
                        direction={sortDirection}
                        label="Dur"
                        onClick={() => handleSort("duration")}
                      />
                    </th>
                    <th>
                      <SortHeader
                        active={sortKey === "status"}
                        direction={sortDirection}
                        label="Status"
                        onClick={() => handleSort("status")}
                      />
                    </th>
                    <th>
                      <SortHeader
                        active={sortKey === "match"}
                        direction={sortDirection}
                        label="SoundCloud Match"
                        onClick={() => handleSort("match")}
                      />
                    </th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleFiles.map((file) => (
                    <UsbFileRow
                      file={file}
                      isSelected={selectedFileIds.has(file.audio_file_id)}
                      key={file.audio_file_id}
                      onMatch={() => void openMatchModal(file)}
                      onPreview={() => handlePreviewAudio(file)}
                      onQuarantine={() => setQuarantineFile(file)}
                      onSelect={() => handleToggleSelected(file.audio_file_id)}
                    />
                  ))}
                </tbody>
              </table>
              {!isLoading && visibleFiles.length === 0 ? (
                <div className="playlist-filter-empty playlist-filter-empty--table">
                  No USB files match the current folder and filters.
                </div>
              ) : null}
            </div>
          </main>
        </div>
      )}

      <MatchModal
        candidates={candidates}
        file={matchFile}
        isMapping={mappingSongId}
        isSearching={isSearchingCandidates}
        query={candidateQuery}
        onClose={() => {
          setMatchFile(null);
          setCandidates([]);
        }}
        onMap={handleMapCandidate}
        onQueryChange={setCandidateQuery}
        onQuarantine={(file) => setQuarantineFile(file)}
        onSearch={handleCandidateSearch}
      />

      <ConfirmDialog
        confirmLabel={isQuarantining ? "Moving..." : "Move to Deprecated"}
        message={
          quarantineFile
            ? `Move ${quarantineFile.filename} into the app-managed deprecated folder and remove any matches that point to it.`
            : ""
        }
        open={quarantineFile !== null}
        title="Move file to deprecated?"
        onCancel={() => setQuarantineFile(null)}
        onConfirm={() => void handleConfirmQuarantine()}
      />

      <ConfirmDialog
        confirmLabel={isBulkQuarantining ? "Moving..." : "Delete Selected"}
        confirmationPlaceholder="delete"
        confirmationRequiredValue="delete"
        confirmationValue={bulkDeleteConfirmation}
        message={
          selectedCount > 0
            ? `Move ${formatNumber(selectedCount)} selected local audio file${
                selectedCount === 1 ? "" : "s"
              } into the app-managed deprecated folder and remove any matches that point to them.`
            : ""
        }
        open={bulkDeleteConfirmOpen}
        title="Delete selected USB files?"
        onCancel={closeBulkDeleteConfirm}
        onConfirmationChange={setBulkDeleteConfirmation}
        onConfirm={() => void handleConfirmBulkQuarantine()}
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

type UsbFileRowProps = {
  file: UsbFileRead;
  isSelected: boolean;
  onMatch: () => void;
  onPreview: () => void;
  onQuarantine: () => void;
  onSelect: () => void;
};

function UsbFileRow({
  file,
  isSelected,
  onMatch,
  onPreview,
  onQuarantine,
  onSelect,
}: UsbFileRowProps) {
  const preview = isLikelyPreview(file);
  const rowClassName = [
    "playlist-track-row",
    file.match_status === "unmatched" ? "is-ambiguous" : "",
    preview ? "usb-row--preview" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <tr className={rowClassName}>
      <td className="selection-cell">
        <input
          aria-label={`Select ${file.filename}`}
          checked={isSelected}
          type="checkbox"
          onChange={onSelect}
        />
      </td>
      <td className="track-title-cell">
        <strong>{file.filename}</strong>
        <span>{file.relative_path}</span>
        {preview ? <em>Likely preview download</em> : null}
      </td>
      <td className="track-duration">{formatDuration(file.duration_seconds)}</td>
      <td>
        {file.match_status === "matched" ? (
          <StatusBadge tone="success">Matched</StatusBadge>
        ) : (
          <StatusBadge tone={preview ? "warning" : "danger"}>
            {preview ? "Preview risk" : "Unmatched"}
          </StatusBadge>
        )}
      </td>
      <td>
        {file.matched_song ? (
          <span className="accepted-audio accepted-audio--ready">
            <CheckCircle2 size={13} />
            <span>
              {file.matched_song.title}
              {file.matched_song.artist ? ` · ${file.matched_song.artist}` : ""}
            </span>
            {file.matched_song.playlists.length > 0 ? (
              <em>{file.matched_song.playlists.join(", ")}</em>
            ) : null}
          </span>
        ) : (
          <span className="accepted-audio accepted-audio--empty">No SoundCloud song mapped</span>
        )}
      </td>
      <td>
        <div className="usb-row-actions">
          <Button icon={<Play size={14} />} onClick={onPreview}>
            Play
          </Button>
          {(file.match_status === "unmatched" || preview) ? (
            <Button icon={<Link2 size={14} />} onClick={onMatch}>
              Match
            </Button>
          ) : null}
          <Button icon={<Trash2 size={14} />} variant="danger" onClick={onQuarantine}>
            Move
          </Button>
        </div>
      </td>
    </tr>
  );
}

type SortHeaderProps = {
  active: boolean;
  direction: SortDirection;
  label: string;
  onClick: () => void;
};

function SortHeader({ active, direction, label, onClick }: SortHeaderProps) {
  return (
    <button
      className={["table-sort-button", active ? "is-active" : ""].filter(Boolean).join(" ")}
      type="button"
      onClick={onClick}
    >
      <span>{label}</span>
      <ArrowDownUp size={13} />
      {active ? <em>{direction === "asc" ? "Asc" : "Desc"}</em> : null}
    </button>
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
          <strong>{preview?.label ?? "No local file selected"}</strong>
          <span>{playbackError ?? preview?.detail ?? "Select a USB audio file to preview."}</span>
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

type MatchModalProps = {
  candidates: UsbSongCandidateRead[];
  file: UsbFileRead | null;
  isMapping: string | null;
  isSearching: boolean;
  query: string;
  onClose: () => void;
  onMap: (candidate: UsbSongCandidateRead) => void;
  onQueryChange: (query: string) => void;
  onQuarantine: (file: UsbFileRead) => void;
  onSearch: (event: FormEvent<HTMLFormElement>) => void;
};

function MatchModal({
  candidates,
  file,
  isMapping,
  isSearching,
  query,
  onClose,
  onMap,
  onQueryChange,
  onQuarantine,
  onSearch,
}: MatchModalProps) {
  if (!file) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <div className="usb-match-dialog" role="dialog" aria-modal="true" aria-labelledby="usb-match-title">
        <header>
          <div>
            <p className="eyebrow">Map USB file</p>
            <h2 id="usb-match-title">{file.filename}</h2>
            <p className="muted">
              {file.title ?? filenameStem(file.filename)}
              {file.artist ? ` · ${file.artist}` : ""} · {formatDuration(file.duration_seconds)}
            </p>
          </div>
          {isLikelyPreview(file) ? (
            <StatusBadge tone="warning">Likely preview</StatusBadge>
          ) : null}
        </header>

        <form className="usb-match-search" onSubmit={onSearch}>
          <label className="playlist-search-field playlist-search-field--wide">
            <Search size={14} />
            <input
              aria-label="Search imported songs"
              placeholder="Search imported SoundCloud songs..."
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
            />
          </label>
          <Button disabled={isSearching} type="submit">
            {isSearching ? "Searching" : "Search"}
          </Button>
        </form>

        <div className="usb-candidate-list">
          {isSearching ? <LoadingState label="Searching candidates" /> : null}
          {!isSearching && candidates.length === 0 ? (
            <EmptyState
              title="No candidate songs found"
              description="Try a different title, artist, or playlist search. You can also move this file to deprecated if it is an unwanted preview."
            />
          ) : null}
          {candidates.map((candidate) => (
            <div className="usb-candidate-card" key={candidate.song_id}>
              <div>
                <strong>{candidate.title}</strong>
                <span>{candidate.artist ?? "Unknown artist"}</span>
                <p>
                  {formatPercent(candidate.confidence)} match
                  {candidate.method ? ` · ${humanize(candidate.method)}` : ""} ·{" "}
                  {formatDuration(candidate.duration_seconds)}
                </p>
                {candidate.playlists.length > 0 ? (
                  <em>{candidate.playlists.join(", ")}</em>
                ) : null}
              </div>
              <Button
                disabled={isMapping === candidate.song_id}
                icon={<Link2 size={14} />}
                onClick={() => onMap(candidate)}
              >
                {isMapping === candidate.song_id ? "Mapping" : "Map File"}
              </Button>
            </div>
          ))}
        </div>

        <footer>
          <Button onClick={onClose}>Close</Button>
          <Button
            icon={<Trash2 size={14} />}
            variant="danger"
            onClick={() => {
              onClose();
              onQuarantine(file);
            }}
          >
            Move to Deprecated
          </Button>
        </footer>
      </div>
    </div>
  );
}

function buildFolderOptions(files: UsbFileRead[]): FolderOption[] {
  const counts = new Map<string, number>();
  counts.set("", files.length);
  for (const file of files) {
    for (let index = 0; index < file.folder_parts.length; index += 1) {
      const key = folderKey(file.folder_parts.slice(0, index + 1));
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  const options: FolderOption[] = [
    { key: "", label: "All files", depth: 0, count: files.length },
    ...[...counts.entries()]
      .filter(([key]) => key !== "")
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, count]) => {
        const parts = key.split("/");
        return { key, label: parts[parts.length - 1], depth: parts.length, count };
      }),
  ];
  return options;
}

function usbCounts(files: UsbFileRead[]) {
  return {
    total: files.length,
    matched: files.filter((file) => file.match_status === "matched").length,
    unmatched: files.filter((file) => file.match_status === "unmatched").length,
    preview: files.filter(isLikelyPreview).length,
  };
}

function compareUsbFiles(
  left: UsbFileRead,
  right: UsbFileRead,
  sortKey: UsbSortKey,
  direction: SortDirection,
) {
  const multiplier = direction === "asc" ? 1 : -1;
  if (sortKey === "duration") {
    return multiplier * compareNullableNumber(left.duration_seconds, right.duration_seconds);
  }
  if (sortKey === "status") {
    return multiplier * (statusRank(left) - statusRank(right));
  }
  if (sortKey === "match") {
    return (
      multiplier *
      compareText(left.matched_song?.title ?? "", right.matched_song?.title ?? "")
    );
  }
  return multiplier * compareText(left.filename, right.filename);
}

function statusRank(file: UsbFileRead) {
  if (isLikelyPreview(file)) {
    return 0;
  }
  return file.match_status === "unmatched" ? 1 : 2;
}

function compareNullableNumber(left: number | null, right: number | null) {
  if (left === null && right === null) {
    return 0;
  }
  if (left === null) {
    return 1;
  }
  if (right === null) {
    return -1;
  }
  return left - right;
}

function compareText(left: string, right: string) {
  return left.localeCompare(right, undefined, { sensitivity: "base", numeric: true });
}

function folderKey(parts: readonly string[]) {
  return parts.join("/");
}

function isLikelyPreview(file: UsbFileRead) {
  return file.warnings.includes("likely_preview_download");
}

function filenameStem(filename: string) {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex > 0 ? filename.slice(0, dotIndex) : filename;
}

function formatDuration(seconds: number | null) {
  if (seconds === null) {
    return "--:--";
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat().format(value);
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function humanize(value: string) {
  return value.replace(/_/g, " ");
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
