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
    LibraryMetadataAsset,
    LibraryMetadataAssetStatus,
    LibraryMetadataImportRun,
    LibraryMetadataImportRunStatus,
    LibraryMetadataIndexEntry,
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

    def delete(self, track_id: str) -> None:
        self.connection.execute(
            "UPDATE library_metadata_index_entries SET library_track_id = NULL WHERE library_track_id = ?",
            (track_id,),
        )
        self.connection.execute(
            "UPDATE library_alignment_items SET library_track_id = NULL WHERE library_track_id = ?",
            (track_id,),
        )
        self.connection.execute(
            "DELETE FROM song_library_links WHERE library_track_id = ?",
            (track_id,),
        )
        self.connection.execute(
            "DELETE FROM library_tracks WHERE id = ?",
            (track_id,),
        )
        self.connection.commit()

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


class SqliteLibraryMetadataRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save_import_run(
        self,
        run: LibraryMetadataImportRun,
        assets: tuple[LibraryMetadataAsset, ...] = (),
        entries: tuple[LibraryMetadataIndexEntry, ...] = (),
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO library_metadata_import_runs (
                id,
                library_id,
                environment_id,
                alignment_run_id,
                status,
                started_at,
                finished_at,
                asset_count,
                index_entry_count,
                error_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                library_id = excluded.library_id,
                environment_id = excluded.environment_id,
                alignment_run_id = excluded.alignment_run_id,
                status = excluded.status,
                started_at = excluded.started_at,
                finished_at = excluded.finished_at,
                asset_count = excluded.asset_count,
                index_entry_count = excluded.index_entry_count,
                error_count = excluded.error_count
            """,
            (
                run.id,
                run.library_id,
                run.environment_id,
                run.alignment_run_id,
                run.status.value,
                run.started_at,
                run.finished_at,
                run.asset_count,
                run.index_entry_count,
                run.error_count,
            ),
        )
        if assets:
            self.connection.execute(
                """
                DELETE FROM library_metadata_index_entries
                WHERE source_asset_id IN (
                    SELECT id FROM library_metadata_assets WHERE run_id = ?
                )
                """,
                (run.id,),
            )
            self.connection.execute(
                "DELETE FROM library_metadata_assets WHERE run_id = ?",
                (run.id,),
            )
            self.connection.executemany(
                """
                INSERT INTO library_metadata_assets (
                    id,
                    run_id,
                    library_id,
                    provider,
                    asset_type,
                    source_path,
                    stored_path,
                    size_bytes,
                    modified_at,
                    imported_at,
                    status,
                    error_code,
                    error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        asset.id,
                        asset.run_id,
                        asset.library_id,
                        asset.provider,
                        asset.asset_type,
                        str(asset.source_path),
                        str(asset.stored_path) if asset.stored_path is not None else None,
                        asset.size_bytes,
                        asset.modified_at,
                        asset.imported_at,
                        asset.status.value,
                        asset.error_code,
                        asset.error_message,
                    )
                    for asset in assets
                ],
            )
        if entries:
            self.connection.executemany(
                """
                INSERT INTO library_metadata_index_entries (
                    id,
                    library_id,
                    provider,
                    source_asset_id,
                    source_path,
                    library_track_id,
                    entry_key,
                    payload_json,
                    imported_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(library_id, provider, entry_key) DO UPDATE SET
                    id = excluded.id,
                    source_asset_id = excluded.source_asset_id,
                    source_path = excluded.source_path,
                    library_track_id = excluded.library_track_id,
                    payload_json = excluded.payload_json,
                    imported_at = excluded.imported_at
                """,
                [
                    (
                        entry.id,
                        entry.library_id,
                        entry.provider,
                        entry.source_asset_id,
                        str(entry.source_path),
                        entry.library_track_id,
                        entry.entry_key,
                        entry.payload_json,
                        entry.imported_at,
                    )
                    for entry in entries
                ],
            )
        self.connection.commit()

    def latest(
        self,
        library_id: str,
    ) -> tuple[
        LibraryMetadataImportRun,
        tuple[LibraryMetadataAsset, ...],
        tuple[LibraryMetadataIndexEntry, ...],
    ] | None:
        row = self.connection.execute(
            """
            SELECT * FROM library_metadata_import_runs
            WHERE library_id = ?
            ORDER BY started_at DESC, id DESC
            LIMIT 1
            """,
            (library_id,),
        ).fetchone()
        if row is None:
            return None
        return self._run_bundle(_metadata_run_from_row(row))

    def latest_by_alignment_run(
        self,
        alignment_run_id: str,
    ) -> tuple[
        LibraryMetadataImportRun,
        tuple[LibraryMetadataAsset, ...],
        tuple[LibraryMetadataIndexEntry, ...],
    ] | None:
        row = self.connection.execute(
            """
            SELECT * FROM library_metadata_import_runs
            WHERE alignment_run_id = ?
            ORDER BY started_at DESC, id DESC
            LIMIT 1
            """,
            (alignment_run_id,),
        ).fetchone()
        if row is None:
            return None
        return self._run_bundle(_metadata_run_from_row(row))

    def count_assets(self, library_id: str) -> int:
        row = self.connection.execute(
            """
            SELECT COUNT(*) FROM library_metadata_assets
            WHERE library_id = ? AND status = ?
            """,
            (library_id, LibraryMetadataAssetStatus.COPIED.value),
        ).fetchone()
        return int(row[0])

    def count_index_entries(self, library_id: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM library_metadata_index_entries WHERE library_id = ?",
            (library_id,),
        ).fetchone()
        return int(row[0])

    def last_imported_at(self, library_id: str) -> str | None:
        row = self.connection.execute(
            """
            SELECT MAX(finished_at) FROM library_metadata_import_runs
            WHERE library_id = ? AND finished_at IS NOT NULL
            """,
            (library_id,),
        ).fetchone()
        return cast(str | None, row[0])

    def list_assets(self, library_id: str) -> list[LibraryMetadataAsset]:
        rows = self.connection.execute(
            """
            SELECT * FROM library_metadata_assets
            WHERE library_id = ?
            ORDER BY imported_at DESC, source_path, id
            """,
            (library_id,),
        ).fetchall()
        return [_metadata_asset_from_row(row) for row in rows]

    def list_index_entries(self, library_id: str) -> list[LibraryMetadataIndexEntry]:
        rows = self.connection.execute(
            """
            SELECT * FROM library_metadata_index_entries
            WHERE library_id = ?
            ORDER BY imported_at DESC, provider, entry_key, id
            """,
            (library_id,),
        ).fetchall()
        return [_metadata_entry_from_row(row) for row in rows]

    def _run_bundle(
        self,
        run: LibraryMetadataImportRun,
    ) -> tuple[
        LibraryMetadataImportRun,
        tuple[LibraryMetadataAsset, ...],
        tuple[LibraryMetadataIndexEntry, ...],
    ]:
        return run, tuple(self._assets_for_run(run.id)), tuple(self._entries_for_run(run.id))

    def _assets_for_run(self, run_id: str) -> list[LibraryMetadataAsset]:
        rows = self.connection.execute(
            """
            SELECT * FROM library_metadata_assets
            WHERE run_id = ?
            ORDER BY source_path, id
            """,
            (run_id,),
        ).fetchall()
        return [_metadata_asset_from_row(row) for row in rows]

    def _entries_for_run(self, run_id: str) -> list[LibraryMetadataIndexEntry]:
        rows = self.connection.execute(
            """
            SELECT library_metadata_index_entries.* FROM library_metadata_index_entries
            JOIN library_metadata_assets
                ON library_metadata_assets.id = library_metadata_index_entries.source_asset_id
            WHERE library_metadata_assets.run_id = ?
            ORDER BY library_metadata_index_entries.entry_key
            """,
            (run_id,),
        ).fetchall()
        return [_metadata_entry_from_row(row) for row in rows]


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


def _metadata_run_from_row(row: sqlite3.Row) -> LibraryMetadataImportRun:
    return LibraryMetadataImportRun(
        id=cast(str, row["id"]),
        library_id=cast(str, row["library_id"]),
        environment_id=cast(str, row["environment_id"]),
        alignment_run_id=cast(str | None, row["alignment_run_id"]),
        status=LibraryMetadataImportRunStatus(cast(str, row["status"])),
        started_at=cast(str, row["started_at"]),
        finished_at=cast(str | None, row["finished_at"]),
        asset_count=cast(int, row["asset_count"]),
        index_entry_count=cast(int, row["index_entry_count"]),
        error_count=cast(int, row["error_count"]),
    )


def _metadata_asset_from_row(row: sqlite3.Row) -> LibraryMetadataAsset:
    stored_path = cast(str | None, row["stored_path"])
    return LibraryMetadataAsset(
        id=cast(str, row["id"]),
        run_id=cast(str, row["run_id"]),
        library_id=cast(str, row["library_id"]),
        provider=cast(str, row["provider"]),
        asset_type=cast(str, row["asset_type"]),
        source_path=Path(cast(str, row["source_path"])),
        stored_path=Path(stored_path) if stored_path is not None else None,
        size_bytes=cast(int, row["size_bytes"]),
        modified_at=cast(float, row["modified_at"]),
        imported_at=cast(str, row["imported_at"]),
        status=LibraryMetadataAssetStatus(cast(str, row["status"])),
        error_code=cast(str | None, row["error_code"]),
        error_message=cast(str | None, row["error_message"]),
    )


def _metadata_entry_from_row(row: sqlite3.Row) -> LibraryMetadataIndexEntry:
    return LibraryMetadataIndexEntry(
        id=cast(str, row["id"]),
        library_id=cast(str, row["library_id"]),
        provider=cast(str, row["provider"]),
        source_asset_id=cast(str, row["source_asset_id"]),
        source_path=Path(cast(str, row["source_path"])),
        library_track_id=cast(str | None, row["library_track_id"]),
        entry_key=cast(str, row["entry_key"]),
        payload_json=cast(str, row["payload_json"]),
        imported_at=cast(str, row["imported_at"]),
    )
