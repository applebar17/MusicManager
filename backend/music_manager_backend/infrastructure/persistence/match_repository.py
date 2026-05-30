import sqlite3
from typing import cast

from music_manager_backend.domain.entities import MatchLink


class SqliteMatchLinkRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save(self, match_link: MatchLink) -> None:
        self.connection.execute(
            """
            INSERT INTO match_links (song_id, audio_file_id, method, confidence, reviewed)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(song_id, audio_file_id) DO UPDATE SET
                method = excluded.method,
                confidence = excluded.confidence,
                reviewed = excluded.reviewed
            """,
            (
                match_link.song_id,
                match_link.audio_file_id,
                match_link.method,
                match_link.confidence,
                int(match_link.reviewed),
            ),
        )
        self.connection.commit()

    def list_by_song(self, song_id: str) -> list[MatchLink]:
        rows = self.connection.execute(
            "SELECT * FROM match_links WHERE song_id = ? ORDER BY confidence DESC, audio_file_id",
            (song_id,),
        ).fetchall()
        return [
            MatchLink(
                song_id=cast(str, row["song_id"]),
                audio_file_id=cast(str, row["audio_file_id"]),
                method=cast(str, row["method"]),
                confidence=cast(float, row["confidence"]),
                reviewed=bool(cast(int, row["reviewed"])),
            )
            for row in rows
        ]

    def delete_automatic_by_song(self, song_id: str) -> None:
        self.connection.execute(
            "DELETE FROM match_links WHERE song_id = ? AND reviewed = 0",
            (song_id,),
        )
        self.connection.commit()

    def delete_automatic_by_song_audio_files(
        self, song_id: str, audio_file_ids: set[str]
    ) -> None:
        if not audio_file_ids:
            return
        placeholders = ", ".join("?" for _ in audio_file_ids)
        self.connection.execute(
            f"""
            DELETE FROM match_links
            WHERE song_id = ?
                AND reviewed = 0
                AND audio_file_id IN ({placeholders})
            """,
            (song_id, *sorted(audio_file_ids)),
        )
        self.connection.commit()

    def delete_by_audio_file(self, audio_file_id: str) -> None:
        self.connection.execute(
            "DELETE FROM match_links WHERE audio_file_id = ?",
            (audio_file_id,),
        )
        self.connection.commit()

    def replace_for_song(self, match_link: MatchLink) -> None:
        self.connection.execute("DELETE FROM match_links WHERE song_id = ?", (match_link.song_id,))
        self.connection.execute(
            """
            INSERT INTO match_links (song_id, audio_file_id, method, confidence, reviewed)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                match_link.song_id,
                match_link.audio_file_id,
                match_link.method,
                match_link.confidence,
                int(match_link.reviewed),
            ),
        )
        self.connection.commit()
