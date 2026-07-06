from __future__ import annotations

import argparse
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from music_manager_backend.domain.services.title_normalizer import normalize_match_title
from music_manager_backend.shared.settings import get_settings
from music_manager_backend.shared.time import utc_now_iso


@dataclass(frozen=True)
class LibraryTrackCandidate:
    id: str
    canonical_path: str
    filename: str
    normalized_title: str | None
    duration_seconds: int | None


@dataclass(frozen=True)
class PortCandidate:
    song_id: str
    library_track_id: str
    method: str
    confidence: float


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Port reviewed legacy audio-file match links to reviewed shared-library mappings."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=get_settings().database_path,
        help="SQLite database path. Defaults to MUSIC_MANAGER_DATABASE_PATH or local/music-manager.sqlite3.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be ported without writing song_library_links.",
    )
    args = parser.parse_args()

    database_path = args.database
    if not database_path.exists():
        raise SystemExit(f"Database not found: {database_path}")

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        report = port_manual_audio_links(connection, dry_run=args.dry_run)
        if not args.dry_run:
            connection.commit()

    mode = "dry run" if args.dry_run else "written"
    print(f"Manual mapping port {mode}")
    print(f"  reviewed legacy links: {report['reviewed_legacy_links']}")
    print(f"  songs ported:          {report['ported']}")
    print(f"  existing manual kept:  {report['existing_manual']}")
    print(f"  skipped ambiguous:     {report['ambiguous']}")
    print(f"  skipped unresolved:    {report['unresolved']}")

    if report["examples"]:
        print()
        print("Examples:")
        for example in report["examples"][:20]:
            print(f"  {example}")


def port_manual_audio_links(
    connection: sqlite3.Connection,
    *,
    dry_run: bool,
) -> dict[str, object]:
    tracks = _active_library_tracks(connection)
    by_path = {track.canonical_path: track for track in tracks}
    by_identity = _group_by_identity(tracks, title_attr="normalized_title")
    by_filename_identity = _group_by_identity(tracks, title_attr="filename_identity")
    by_filename = defaultdict(list)
    for track in tracks:
        by_filename[track.filename.casefold()].append(track)

    rows = connection.execute(
        """
        SELECT
            match_links.song_id,
            match_links.method,
            match_links.confidence,
            audio_files.path AS audio_path,
            audio_files.title AS audio_title,
            audio_files.duration_seconds AS audio_duration_seconds
        FROM match_links
        JOIN audio_files ON audio_files.id = match_links.audio_file_id
        WHERE match_links.reviewed = 1
        ORDER BY match_links.song_id, audio_files.path
        """
    ).fetchall()

    existing_manual = {
        row["song_id"]
        for row in connection.execute(
            """
            SELECT song_id
            FROM song_library_links
            WHERE reviewed = 1 AND method = 'manual'
            """
        ).fetchall()
    }

    candidates_by_song: dict[str, list[PortCandidate]] = defaultdict(list)
    unresolved = 0
    examples: list[str] = []
    for row in rows:
        song_id = str(row["song_id"])
        if song_id in existing_manual:
            continue
        candidate = _candidate_for_legacy_link(
            row=row,
            by_path=by_path,
            by_identity=by_identity,
            by_filename_identity=by_filename_identity,
            by_filename=by_filename,
        )
        if candidate is None:
            unresolved += 1
            if len(examples) < 20:
                examples.append(f"unresolved {song_id}: {row['audio_path']}")
            continue
        candidates_by_song[song_id].append(candidate)

    ported = 0
    ambiguous = 0
    migrated_at = utc_now_iso()
    for song_id, candidates in candidates_by_song.items():
        unique_track_ids = {candidate.library_track_id for candidate in candidates}
        if len(unique_track_ids) != 1:
            ambiguous += 1
            if len(examples) < 20:
                examples.append(
                    f"ambiguous {song_id}: {', '.join(sorted(unique_track_ids))}"
                )
            continue

        candidate = candidates[0]
        ported += 1
        if dry_run:
            if len(examples) < 20:
                examples.append(
                    f"would port {song_id} -> {candidate.library_track_id} via {candidate.method}"
                )
            continue

        connection.execute(
            """
            INSERT INTO song_library_links (
                song_id,
                library_track_id,
                method,
                confidence,
                reviewed,
                created_at,
                updated_at
            )
            VALUES (?, ?, 'manual', ?, 1, ?, ?)
            ON CONFLICT(song_id, library_track_id) DO UPDATE SET
                method = 'manual',
                confidence = excluded.confidence,
                reviewed = 1,
                updated_at = excluded.updated_at
            """,
            (
                candidate.song_id,
                candidate.library_track_id,
                candidate.confidence,
                migrated_at,
                migrated_at,
            ),
        )
        if len(examples) < 20:
            examples.append(
                f"ported {song_id} -> {candidate.library_track_id} via {candidate.method}"
            )

    return {
        "reviewed_legacy_links": len(rows),
        "ported": ported,
        "existing_manual": len(existing_manual),
        "ambiguous": ambiguous,
        "unresolved": unresolved,
        "examples": examples,
    }


def _candidate_for_legacy_link(
    *,
    row: sqlite3.Row,
    by_path: dict[str, LibraryTrackCandidate],
    by_identity: dict[tuple[str, int], list[LibraryTrackCandidate]],
    by_filename_identity: dict[tuple[str, int], list[LibraryTrackCandidate]],
    by_filename: dict[str, list[LibraryTrackCandidate]],
) -> PortCandidate | None:
    audio_path = str(row["audio_path"])
    path_match = by_path.get(audio_path)
    if path_match is not None:
        return _port_candidate(row, path_match, "legacy_path_exact")

    duration = row["audio_duration_seconds"]
    if duration is not None:
        title_identity = normalize_match_title(str(row["audio_title"] or ""))
        if title_identity:
            title_match = _unique(by_identity.get((title_identity, int(duration)), []))
            if title_match is not None:
                return _port_candidate(row, title_match, "legacy_title_duration")

        filename_identity = _filename_identity(audio_path)
        if filename_identity:
            filename_identity_match = _unique(
                by_filename_identity.get((filename_identity, int(duration)), [])
            )
            if filename_identity_match is not None:
                return _port_candidate(
                    row,
                    filename_identity_match,
                    "legacy_filename_duration",
                )

    filename_match = _unique(by_filename.get(_filename(audio_path).casefold(), []))
    if filename_match is not None:
        return _port_candidate(row, filename_match, "legacy_filename_exact")

    return None


def _port_candidate(
    row: sqlite3.Row,
    track: LibraryTrackCandidate,
    method: str,
) -> PortCandidate:
    return PortCandidate(
        song_id=str(row["song_id"]),
        library_track_id=track.id,
        method=method,
        confidence=float(row["confidence"] or 1.0),
    )


def _active_library_tracks(connection: sqlite3.Connection) -> list[LibraryTrackCandidate]:
    return [
        LibraryTrackCandidate(
            id=str(row["id"]),
            canonical_path=str(row["canonical_path"]),
            filename=str(row["filename"]),
            normalized_title=row["normalized_title"],
            duration_seconds=row["duration_seconds"],
        )
        for row in connection.execute(
            """
            SELECT id, canonical_path, filename, normalized_title, duration_seconds
            FROM library_tracks
            WHERE status = 'active'
            """
        ).fetchall()
    ]


def _group_by_identity(
    tracks: list[LibraryTrackCandidate],
    *,
    title_attr: str,
) -> dict[tuple[str, int], list[LibraryTrackCandidate]]:
    grouped: dict[tuple[str, int], list[LibraryTrackCandidate]] = defaultdict(list)
    for track in tracks:
        duration = track.duration_seconds
        if duration is None:
            continue
        if title_attr == "normalized_title":
            identity = track.normalized_title
        else:
            identity = _filename_identity(track.canonical_path)
        if identity:
            grouped[(identity, int(duration))].append(track)
    return grouped


def _unique(candidates: list[LibraryTrackCandidate]) -> LibraryTrackCandidate | None:
    return candidates[0] if len(candidates) == 1 else None


def _filename_identity(path: str) -> str:
    stem = Path(_filename(path)).stem
    return normalize_match_title(_DUPLICATE_SUFFIX_RE.sub("", stem))


def _filename(path: str) -> str:
    posix_name = PurePosixPath(path).name
    windows_name = PureWindowsPath(path).name
    return windows_name if len(windows_name) < len(posix_name) else posix_name


_DUPLICATE_SUFFIX_RE = re.compile(r"\s+\(\d+\)$")


if __name__ == "__main__":
    main()
