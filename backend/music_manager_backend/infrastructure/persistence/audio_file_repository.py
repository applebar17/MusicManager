import sqlite3
from pathlib import Path
from typing import cast

from music_manager_backend.domain.entities import AudioFile


class SqliteAudioFileRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, audio_file: AudioFile) -> None:
        self.connection.execute(
            """
            INSERT INTO audio_files (
                id,
                environment_id,
                path,
                size_bytes,
                modified_at,
                title,
                artist,
                duration_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                environment_id = excluded.environment_id,
                path = excluded.path,
                size_bytes = excluded.size_bytes,
                modified_at = excluded.modified_at,
                title = excluded.title,
                artist = excluded.artist,
                duration_seconds = excluded.duration_seconds
            """,
            (
                audio_file.id,
                audio_file.environment_id,
                str(audio_file.path),
                audio_file.size_bytes,
                audio_file.modified_at,
                audio_file.title,
                audio_file.artist,
                audio_file.duration_seconds,
            ),
        )
        self.connection.commit()

    def get(self, audio_file_id: str) -> AudioFile | None:
        row = self.connection.execute(
            "SELECT * FROM audio_files WHERE id = ?",
            (audio_file_id,),
        ).fetchone()
        if row is None:
            return None
        return _audio_file_from_row(row)

    def list_by_environment(self, environment_id: str) -> list[AudioFile]:
        rows = self.connection.execute(
            "SELECT * FROM audio_files WHERE environment_id = ? ORDER BY path, id",
            (environment_id,),
        ).fetchall()
        return [_audio_file_from_row(row) for row in rows]


def _audio_file_from_row(row: sqlite3.Row) -> AudioFile:
    return AudioFile(
        id=cast(str, row["id"]),
        environment_id=cast(str, row["environment_id"]),
        path=Path(cast(str, row["path"])),
        size_bytes=cast(int, row["size_bytes"]),
        modified_at=cast(float, row["modified_at"]),
        title=cast(str | None, row["title"]),
        artist=cast(str | None, row["artist"]),
        duration_seconds=cast(int | None, row["duration_seconds"]),
    )
