import sqlite3
from typing import cast

from music_manager_backend.domain.entities import RemotePlaylist


class SqliteRemotePlaylistRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, remote_playlist: RemotePlaylist) -> None:
        self.connection.execute(
            """
            INSERT INTO remote_playlists (id, source, source_url, name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source = excluded.source,
                source_url = excluded.source_url,
                name = excluded.name
            """,
            (
                remote_playlist.id,
                remote_playlist.source,
                remote_playlist.source_url,
                remote_playlist.name,
            ),
        )
        self.connection.commit()

    def get(self, remote_playlist_id: str) -> RemotePlaylist | None:
        row = self.connection.execute(
            "SELECT * FROM remote_playlists WHERE id = ?",
            (remote_playlist_id,),
        ).fetchone()
        return _remote_playlist_from_row(row)

    def get_by_source_url(self, source: str, source_url: str) -> RemotePlaylist | None:
        row = self.connection.execute(
            """
            SELECT * FROM remote_playlists
            WHERE source = ? AND source_url = ?
            ORDER BY id
            LIMIT 1
            """,
            (source, source_url),
        ).fetchone()
        return _remote_playlist_from_row(row)


def _remote_playlist_from_row(row: sqlite3.Row | None) -> RemotePlaylist | None:
    if row is None:
        return None
    return RemotePlaylist(
        id=cast(str, row["id"]),
        source=cast(str, row["source"]),
        source_url=cast(str, row["source_url"]),
        name=cast(str, row["name"]),
    )
