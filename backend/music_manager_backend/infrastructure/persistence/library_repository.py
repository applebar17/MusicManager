from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import cast

from music_manager_backend.domain.entities.library import (
    DEFAULT_LIBRARY_ID,
    LibraryTrack,
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
                title,
                artist,
                duration_seconds,
                normalized_title,
                file_hash,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                library_id = excluded.library_id,
                canonical_path = excluded.canonical_path,
                filename = excluded.filename,
                title = excluded.title,
                artist = excluded.artist,
                duration_seconds = excluded.duration_seconds,
                normalized_title = excluded.normalized_title,
                file_hash = excluded.file_hash,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at
            """,
            (
                track.id,
                track.library_id,
                str(track.canonical_path),
                track.filename,
                track.title,
                track.artist,
                track.duration_seconds,
                track.normalized_title,
                track.file_hash,
                track.created_at,
                track.updated_at,
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

    def count(self, library_id: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM library_tracks WHERE library_id = ?",
            (library_id,),
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
            ORDER BY filename, id
            """,
            (library_id, normalized_title, duration_seconds),
        ).fetchall()
        return [_track_from_row(row) for row in rows]


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
        title=cast(str | None, row["title"]),
        artist=cast(str | None, row["artist"]),
        duration_seconds=cast(int | None, row["duration_seconds"]),
        normalized_title=cast(str | None, row["normalized_title"]),
        file_hash=cast(str | None, row["file_hash"]),
        created_at=cast(str, row["created_at"]),
        updated_at=cast(str, row["updated_at"]),
    )
