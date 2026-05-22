import json
import sqlite3
from typing import cast

from music_manager_backend.domain.entities import SyncSnapshot


class SqliteSyncSnapshotRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, snapshot: SyncSnapshot) -> None:
        self.connection.execute(
            """
            INSERT INTO sync_snapshots (
                id,
                source,
                remote_playlist_id,
                captured_at,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source = excluded.source,
                remote_playlist_id = excluded.remote_playlist_id,
                captured_at = excluded.captured_at,
                payload_json = excluded.payload_json
            """,
            (
                snapshot.id,
                snapshot.source,
                snapshot.remote_playlist_id,
                snapshot.captured_at,
                json.dumps(snapshot.payload, sort_keys=True),
            ),
        )
        self.connection.commit()

    def list_by_remote_playlist(self, remote_playlist_id: str) -> list[SyncSnapshot]:
        rows = self.connection.execute(
            """
            SELECT * FROM sync_snapshots
            WHERE remote_playlist_id = ?
            ORDER BY captured_at, id
            """,
            (remote_playlist_id,),
        ).fetchall()
        return [
            SyncSnapshot(
                id=cast(str, row["id"]),
                source=cast(str, row["source"]),
                remote_playlist_id=cast(str, row["remote_playlist_id"]),
                captured_at=cast(str, row["captured_at"]),
                payload=cast(dict[str, object], json.loads(cast(str, row["payload_json"]))),
            )
            for row in rows
        ]
