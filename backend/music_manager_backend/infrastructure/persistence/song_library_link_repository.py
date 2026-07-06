import sqlite3
from datetime import UTC, datetime
from typing import cast

from music_manager_backend.domain.entities import SongLibraryLink


class SqliteSongLibraryLinkRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, link: SongLibraryLink) -> None:
        now = _now()
        created_at = link.created_at or now
        updated_at = link.updated_at or now
        self.connection.execute(
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
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(song_id, library_track_id) DO UPDATE SET
                method = excluded.method,
                confidence = excluded.confidence,
                reviewed = excluded.reviewed,
                updated_at = excluded.updated_at
            """,
            (
                link.song_id,
                link.library_track_id,
                link.method,
                link.confidence,
                int(link.reviewed),
                created_at,
                updated_at,
            ),
        )
        self.connection.commit()

    def list_by_song(self, song_id: str) -> list[SongLibraryLink]:
        rows = self.connection.execute(
            """
            SELECT * FROM song_library_links
            WHERE song_id = ?
            ORDER BY reviewed DESC, confidence DESC, library_track_id
            """,
            (song_id,),
        ).fetchall()
        return [_link_from_row(row) for row in rows]

    def list_by_library_track(self, library_track_id: str) -> list[SongLibraryLink]:
        rows = self.connection.execute(
            """
            SELECT * FROM song_library_links
            WHERE library_track_id = ?
            ORDER BY reviewed DESC, confidence DESC, song_id
            """,
            (library_track_id,),
        ).fetchall()
        return [_link_from_row(row) for row in rows]

    def count_by_library_track_ids(self, library_track_ids: set[str]) -> dict[str, int]:
        if not library_track_ids:
            return {}
        placeholders = ", ".join("?" for _ in library_track_ids)
        rows = self.connection.execute(
            f"""
            SELECT library_track_id, COUNT(DISTINCT song_id) AS mapped_count
            FROM song_library_links
            WHERE library_track_id IN ({placeholders})
            GROUP BY library_track_id
            """,
            tuple(sorted(library_track_ids)),
        ).fetchall()
        return {
            cast(str, row["library_track_id"]): int(row["mapped_count"])
            for row in rows
        }

    def delete_automatic_by_song(self, song_id: str) -> None:
        self.connection.execute(
            "DELETE FROM song_library_links WHERE song_id = ? AND reviewed = 0",
            (song_id,),
        )
        self.connection.commit()

    def replace_for_song(self, link: SongLibraryLink) -> None:
        now = _now()
        created_at = link.created_at or now
        updated_at = link.updated_at or now
        self.connection.execute(
            "DELETE FROM song_library_links WHERE song_id = ?",
            (link.song_id,),
        )
        self.connection.execute(
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
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                link.song_id,
                link.library_track_id,
                link.method,
                link.confidence,
                int(link.reviewed),
                created_at,
                updated_at,
            ),
        )
        self.connection.commit()


def _link_from_row(row: sqlite3.Row) -> SongLibraryLink:
    return SongLibraryLink(
        song_id=cast(str, row["song_id"]),
        library_track_id=cast(str, row["library_track_id"]),
        method=cast(str, row["method"]),
        confidence=cast(float, row["confidence"]),
        reviewed=bool(cast(int, row["reviewed"])),
        created_at=cast(str, row["created_at"]),
        updated_at=cast(str, row["updated_at"]),
    )


def _now() -> str:
    return datetime.now(UTC).isoformat()
