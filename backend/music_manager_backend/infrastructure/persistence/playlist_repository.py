import sqlite3
from typing import cast

from music_manager_backend.domain.entities import Playlist, PlaylistItem


class SqlitePlaylistRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, playlist: Playlist) -> None:
        self.connection.execute(
            """
            INSERT INTO playlists (
                id,
                environment_id,
                name,
                remote_playlist_id,
                local_name_override
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                environment_id = excluded.environment_id,
                name = excluded.name,
                remote_playlist_id = excluded.remote_playlist_id,
                local_name_override = excluded.local_name_override
            """,
            (
                playlist.id,
                playlist.environment_id,
                playlist.name,
                playlist.remote_playlist_id,
                playlist.local_name_override,
            ),
        )
        self.connection.execute("DELETE FROM playlist_items WHERE playlist_id = ?", (playlist.id,))
        for item in playlist.items:
            self.connection.execute(
                """
                INSERT INTO playlist_items (
                    playlist_id,
                    song_id,
                    position,
                    remote_membership_active
                )
                VALUES (?, ?, ?, ?)
                """,
                (playlist.id, item.song_id, item.position, int(item.remote_membership_active)),
            )
        self.connection.commit()

    def get(self, playlist_id: str) -> Playlist | None:
        row = self.connection.execute(
            "SELECT * FROM playlists WHERE id = ?",
            (playlist_id,),
        ).fetchone()
        if row is None:
            return None
        return _playlist_from_row(row, self._items_for_playlist(playlist_id))

    def list_by_environment(self, environment_id: str) -> list[Playlist]:
        rows = self.connection.execute(
            "SELECT * FROM playlists WHERE environment_id = ? ORDER BY name, id",
            (environment_id,),
        ).fetchall()
        return [
            _playlist_from_row(row, self._items_for_playlist(cast(str, row["id"])))
            for row in rows
        ]

    def _items_for_playlist(self, playlist_id: str) -> tuple[PlaylistItem, ...]:
        rows = self.connection.execute(
            """
            SELECT * FROM playlist_items
            WHERE playlist_id = ?
            ORDER BY position, song_id
            """,
            (playlist_id,),
        ).fetchall()
        return tuple(
            PlaylistItem(
                song_id=cast(str, row["song_id"]),
                position=cast(int, row["position"]),
                remote_membership_active=bool(cast(int, row["remote_membership_active"])),
            )
            for row in rows
        )


def _playlist_from_row(row: sqlite3.Row, items: tuple[PlaylistItem, ...]) -> Playlist:
    return Playlist(
        id=cast(str, row["id"]),
        environment_id=cast(str, row["environment_id"]),
        name=cast(str, row["name"]),
        remote_playlist_id=cast(str | None, row["remote_playlist_id"]),
        local_name_override=cast(str | None, row["local_name_override"]),
        items=items,
    )
