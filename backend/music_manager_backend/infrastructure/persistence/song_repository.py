import sqlite3
from typing import cast

from music_manager_backend.domain.entities import SongMaster


class SqliteSongRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, song: SongMaster) -> None:
        self.connection.execute(
            """
            INSERT INTO songs (
                id,
                title,
                artist,
                duration_seconds,
                source_track_id,
                source_url,
                local_title_override,
                local_artist_override
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                artist = excluded.artist,
                duration_seconds = excluded.duration_seconds,
                source_track_id = excluded.source_track_id,
                source_url = excluded.source_url,
                local_title_override = excluded.local_title_override,
                local_artist_override = excluded.local_artist_override
            """,
            (
                song.id,
                song.title,
                song.artist,
                song.duration_seconds,
                song.source_track_id,
                song.source_url,
                song.local_title_override,
                song.local_artist_override,
            ),
        )
        self.connection.commit()

    def get(self, song_id: str) -> SongMaster | None:
        row = self.connection.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
        return _song_from_row(row)

    def get_by_source_url(self, source_url: str) -> SongMaster | None:
        row = self.connection.execute(
            """
            SELECT * FROM songs
            WHERE source_url = ?
            ORDER BY id
            LIMIT 1
            """,
            (source_url,),
        ).fetchone()
        return _song_from_row(row)


def _song_from_row(row: sqlite3.Row | None) -> SongMaster | None:
    if row is None:
        return None
    return SongMaster(
        id=cast(str, row["id"]),
        title=cast(str, row["title"]),
        artist=cast(str | None, row["artist"]),
        duration_seconds=cast(int | None, row["duration_seconds"]),
        source_track_id=cast(str | None, row["source_track_id"]),
        source_url=cast(str | None, row["source_url"]),
        local_title_override=cast(str | None, row["local_title_override"]),
        local_artist_override=cast(str | None, row["local_artist_override"]),
    )
