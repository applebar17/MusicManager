from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import cast

from music_manager_backend.domain.entities.library import (
    DEFAULT_LIBRARY_ID,
    LibraryAlignmentItem,
    LibraryAlignmentItemStatus,
    LibraryAlignmentRun,
    LibraryAlignmentRunStatus,
    LibraryTrack,
    LibraryTrackStatus,
    MusicLibrary,
)


class SqliteLibraryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_default(self) -> MusicLibrary | None:
        row = self.connection.execute(
            "SELECT * FROM libraries WHERE id = ?",
            (DEFAULT_LIBRARY_ID,),
        ).fetchone()
        if row is None:
            return None
        return _library_from_row(row)

    def save_default(self, library: MusicLibrary) -> None:
        self.connection.execute(
            """
            INSERT INTO libraries (id, root_path, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                root_path = excluded.root_path,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at
            """,
            (
                DEFAULT_LIBRARY_ID,
                str(library.root_path),
                library.created_at,
                library.updated_at,
            ),
        )
        self.connection.commit()


class SqliteLibraryTrackRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, track: LibraryTrack) -> None:
        self.connection.execute(
            """
            INSERT INTO library_tracks (
                id,
                library_id,
                canonical_path,
                filename,
                size_bytes,
                modified_at,
                status,
                title,
                artist,
                duration_seconds,
                normalized_title,
                file_hash,
                created_at,
                updated_at,
                first_seen_at,
                last_seen_at,
                missing_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                library_id = excluded.library_id,
                canonical_path = excluded.canonical_path,
                filename = excluded.filename,
                size_bytes = excluded.size_bytes,
                modified_at = excluded.modified_at,
                status = excluded.status,
                title = excluded.title,
                artist = excluded.artist,
                duration_seconds = excluded.duration_seconds,
                normalized_title = excluded.normalized_title,
                file_hash = excluded.file_hash,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                first_seen_at = excluded.first_seen_at,
                last_seen_at = excluded.last_seen_at,
                missing_at = excluded.missing_at
            """,
            (
                track.id,
                track.library_id,
                str(track.canonical_path),
                track.filename,
                track.size_bytes,
                track.modified_at,
                track.status.value,
                track.title,
                track.artist,
                track.duration_seconds,
                track.normalized_title,
                track.file_hash,
                track.created_at,
                track.updated_at,
                track.first_seen_at,
                track.last_seen_at,
                track.missing_at,
            ),
        )
        self.connection.commit()

    def get(self, track_id: str) -> LibraryTrack | None:
        row = self.connection.execute(
            "SELECT * FROM library_tracks WHERE id = ?",
            (track_id,),
        ).fetchone()
        if row is None:
            return None
        return _track_from_row(row)

    def get_by_canonical_path(self, library_id: str, canonical_path: Path) -> LibraryTrack | None:
        row = self.connection.execute(
            """
            SELECT * FROM library_tracks
            WHERE library_id = ? AND canonical_path = ?
            """,
            (library_id, str(canonical_path)),
        ).fetchone()
        if row is None:
            return None
        return _track_from_row(row)

    def list(self, library_id: str) -> list[LibraryTrack]:
        rows = self.connection.execute(
            """
            SELECT * FROM library_tracks
            WHERE library_id = ?
            ORDER BY filename, id
            """,
            (library_id,),
        ).fetchall()
        return [_track_from_row(row) for row in rows]

    def list_by_status(
        self,
        library_id: str,
        status: LibraryTrackStatus,
    ) -> list[LibraryTrack]:
        rows = self.connection.execute(
            """
            SELECT * FROM library_tracks
            WHERE library_id = ? AND status = ?
            ORDER BY filename, id
            """,
            (library_id, status.value),
        ).fetchall()
        return [_track_from_row(row) for row in rows]

    def count(self, library_id: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM library_tracks WHERE library_id = ? AND status = ?",
            (library_id, LibraryTrackStatus.ACTIVE.value),
        ).fetchone()
        return int(row[0])

    def count_by_status(self, library_id: str, status: LibraryTrackStatus) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM library_tracks WHERE library_id = ? AND status = ?",
            (library_id, status.value),
        ).fetchone()
        return int(row[0])

    def get_by_identity(
        self,
        library_id: str,
        normalized_title: str,
        duration_seconds: int,
    ) -> list[LibraryTrack]:
        rows = self.connection.execute(
            """
            SELECT * FROM library_tracks
            WHERE library_id = ?
                AND normalized_title = ?
                AND duration_seconds = ?
                AND status = ?
            ORDER BY filename, id
            """,
            (
                library_id,
                normalized_title,
                duration_seconds,
                LibraryTrackStatus.ACTIVE.value,
            ),
        ).fetchall()
        return [_track_from_row(row) for row in rows]


class SqliteLibraryAlignmentRunRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, run: LibraryAlignmentRun, items: tuple[LibraryAlignmentItem, ...] = ()) -> None:
        self.connection.execute(
            """
            INSERT INTO library_alignment_runs (
                id,
                library_id,
                environment_id,
                status,
                started_at,
                finished_at,
                scanned_library_count,
                scanned_usb_count,
                copied_count,
                reused_count,
                updated_count,
                skipped_collision_count,
                skipped_error_count,
                warning_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                library_id = excluded.library_id,
                environment_id = excluded.environment_id,
                status = excluded.status,
                started_at = excluded.started_at,
                finished_at = excluded.finished_at,
                scanned_library_count = excluded.scanned_library_count,
                scanned_usb_count = excluded.scanned_usb_count,
                copied_count = excluded.copied_count,
                reused_count = excluded.reused_count,
                updated_count = excluded.updated_count,
                skipped_collision_count = excluded.skipped_collision_count,
                skipped_error_count = excluded.skipped_error_count,
                warning_count = excluded.warning_count
            """,
            (
                run.id,
                run.library_id,
                run.environment_id,
                run.status.value,
                run.started_at,
                run.finished_at,
                run.scanned_library_count,
                run.scanned_usb_count,
                run.copied_count,
                run.reused_count,
                run.updated_count,
                run.skipped_collision_count,
                run.skipped_error_count,
                run.warning_count,
            ),
        )
        if items:
            self.connection.execute(
                "DELETE FROM library_alignment_items WHERE run_id = ?",
                (run.id,),
            )
            self.connection.executemany(
                """
                INSERT INTO library_alignment_items (
                    id,
                    run_id,
                    status,
                    source_path,
                    target_path,
                    library_track_id,
                    reason_code,
                    reason_message,
                    title,
                    artist,
                    duration_seconds,
                    normalized_title
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.id,
                        item.run_id,
                        item.status.value,
                        str(item.source_path),
                        str(item.target_path) if item.target_path is not None else None,
                        item.library_track_id,
                        item.reason_code,
                        item.reason_message,
                        item.title,
                        item.artist,
                        item.duration_seconds,
                        item.normalized_title,
                    )
                    for item in items
                ],
            )
        self.connection.commit()

    def get(self, run_id: str) -> tuple[LibraryAlignmentRun, tuple[LibraryAlignmentItem, ...]] | None:
        row = self.connection.execute(
            "SELECT * FROM library_alignment_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return _run_from_row(row), tuple(self._items_for_run(run_id))

    def latest(self, library_id: str) -> tuple[LibraryAlignmentRun, tuple[LibraryAlignmentItem, ...]] | None:
        row = self.connection.execute(
            """
            SELECT * FROM library_alignment_runs
            WHERE library_id = ?
            ORDER BY started_at DESC, id DESC
            LIMIT 1
            """,
            (library_id,),
        ).fetchone()
        if row is None:
            return None
        run = _run_from_row(row)
        return run, tuple(self._items_for_run(run.id))

    def _items_for_run(self, run_id: str) -> list[LibraryAlignmentItem]:
        rows = self.connection.execute(
            """
            SELECT * FROM library_alignment_items
            WHERE run_id = ?
            ORDER BY id
            """,
            (run_id,),
        ).fetchall()
        return [_item_from_row(row) for row in rows]


def _library_from_row(row: sqlite3.Row) -> MusicLibrary:
    return MusicLibrary(
        id=cast(str, row["id"]),
        root_path=Path(cast(str, row["root_path"])),
        created_at=cast(str, row["created_at"]),
        updated_at=cast(str, row["updated_at"]),
    )


def _track_from_row(row: sqlite3.Row) -> LibraryTrack:
    return LibraryTrack(
        id=cast(str, row["id"]),
        library_id=cast(str, row["library_id"]),
        canonical_path=Path(cast(str, row["canonical_path"])),
        filename=cast(str, row["filename"]),
        size_bytes=cast(int, row["size_bytes"]),
        modified_at=cast(float, row["modified_at"]),
        status=LibraryTrackStatus(cast(str, row["status"])),
        title=cast(str | None, row["title"]),
        artist=cast(str | None, row["artist"]),
        duration_seconds=cast(int | None, row["duration_seconds"]),
        normalized_title=cast(str | None, row["normalized_title"]),
        file_hash=cast(str | None, row["file_hash"]),
        created_at=cast(str, row["created_at"]),
        updated_at=cast(str, row["updated_at"]),
        first_seen_at=cast(str | None, row["first_seen_at"]),
        last_seen_at=cast(str | None, row["last_seen_at"]),
        missing_at=cast(str | None, row["missing_at"]),
    )


def _run_from_row(row: sqlite3.Row) -> LibraryAlignmentRun:
    return LibraryAlignmentRun(
        id=cast(str, row["id"]),
        library_id=cast(str, row["library_id"]),
        environment_id=cast(str, row["environment_id"]),
        status=LibraryAlignmentRunStatus(cast(str, row["status"])),
        started_at=cast(str, row["started_at"]),
        finished_at=cast(str | None, row["finished_at"]),
        scanned_library_count=cast(int, row["scanned_library_count"]),
        scanned_usb_count=cast(int, row["scanned_usb_count"]),
        copied_count=cast(int, row["copied_count"]),
        reused_count=cast(int, row["reused_count"]),
        updated_count=cast(int, row["updated_count"]),
        skipped_collision_count=cast(int, row["skipped_collision_count"]),
        skipped_error_count=cast(int, row["skipped_error_count"]),
        warning_count=cast(int, row["warning_count"]),
    )


def _item_from_row(row: sqlite3.Row) -> LibraryAlignmentItem:
    target_path = cast(str | None, row["target_path"])
    return LibraryAlignmentItem(
        id=cast(str, row["id"]),
        run_id=cast(str, row["run_id"]),
        status=LibraryAlignmentItemStatus(cast(str, row["status"])),
        source_path=Path(cast(str, row["source_path"])),
        target_path=Path(target_path) if target_path is not None else None,
        library_track_id=cast(str | None, row["library_track_id"]),
        reason_code=cast(str | None, row["reason_code"]),
        reason_message=cast(str | None, row["reason_message"]),
        title=cast(str | None, row["title"]),
        artist=cast(str | None, row["artist"]),
        duration_seconds=cast(int | None, row["duration_seconds"]),
        normalized_title=cast(str | None, row["normalized_title"]),
    )
