import {
  AlertTriangle,
  CheckCircle2,
  Folder,
  FolderTree,
  Link2,
  RefreshCw,
  Search,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../../shared/api/http";
import type { UsbFileRead, UsbSongCandidateRead } from "../../shared/api/types";
import { useAppState } from "../../shared/state";
import { Button, ConfirmDialog, EmptyState, ErrorBanner, LoadingState, Panel, StatusBadge } from "../../shared/ui";
import { createManualMapping } from "../matching/api";
import { listUsbFiles, listUsbMatchCandidates, quarantineUsbAudioFile } from "./api";

type UsbStatusFilter = "all" | "matched" | "unmatched" | "preview";

type FolderOption = {
  key: string;
  label: string;
  depth: number;
  count: number;
};

export function UsbFilesPanel() {
  const { selectedEnvironmentId } = useAppState();
  const [files, setFiles] = useState<UsbFileRead[]>([]);
  const [selectedFolderKey, setSelectedFolderKey] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<UsbStatusFilter>("all");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matchFile, setMatchFile] = useState<UsbFileRead | null>(null);
  const [candidateQuery, setCandidateQuery] = useState("");
  const [candidates, setCandidates] = useState<UsbSongCandidateRead[]>([]);
  const [isSearchingCandidates, setIsSearchingCandidates] = useState(false);
  const [mappingSongId, setMappingSongId] = useState<string | null>(null);
  const [quarantineFile, setQuarantineFile] = useState<UsbFileRead | null>(null);
  const [isQuarantining, setIsQuarantining] = useState(false);

  const refreshFiles = useCallback(
    async (environmentId: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const rows = await listUsbFiles(environmentId);
        setFiles(rows);
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
      return;
    }
    void refreshFiles(selectedEnvironmentId);
  }, [refreshFiles, selectedEnvironmentId]);

  const folders = useMemo(() => buildFolderOptions(files), [files]);
  const counts = useMemo(() => usbCounts(files), [files]);
  const visibleFiles = useMemo(
    () =>
      files.filter((file) => {
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
      }),
    [files, search, selectedFolderKey, statusFilter],
  );

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
      if (matchFile?.audio_file_id === quarantineFile.audio_file_id) {
        setMatchFile(null);
      }
      setQuarantineFile(null);
    } catch (quarantineError) {
      setError(errorMessage(quarantineError));
    } finally {
      setIsQuarantining(false);
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
                <span className="playlist-chip playlist-chip--neutral">{formatNumber(counts.total)} Files</span>
                <span className="playlist-chip playlist-chip--success">{formatNumber(counts.matched)} Matched</span>
                <span className="playlist-chip playlist-chip--danger">{formatNumber(counts.unmatched)} Unmatched</span>
                <span className="playlist-chip playlist-chip--warning">{formatNumber(counts.preview)} Preview risk</span>
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
            </div>

            <div className="playlist-table-wrap">
              <table className="playlist-table usb-table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Metadata</th>
                    <th>Dur</th>
                    <th>Status</th>
                    <th>SoundCloud Match</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleFiles.map((file) => (
                    <UsbFileRow
                      file={file}
                      key={file.audio_file_id}
                      onMatch={() => void openMatchModal(file)}
                      onQuarantine={() => setQuarantineFile(file)}
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
    </div>
  );
}

type UsbFileRowProps = {
  file: UsbFileRead;
  onMatch: () => void;
  onQuarantine: () => void;
};

function UsbFileRow({ file, onMatch, onQuarantine }: UsbFileRowProps) {
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
      <td className="track-title-cell">
        <strong>{file.filename}</strong>
        <span>{file.relative_path}</span>
        {preview ? <em>Likely preview download</em> : null}
      </td>
      <td className="track-title-cell">
        <strong>{file.title ?? filenameStem(file.filename)}</strong>
        <span>{file.artist ?? "Unknown artist"}</span>
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
