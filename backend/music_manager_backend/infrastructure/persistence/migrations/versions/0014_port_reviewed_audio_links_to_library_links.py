"""Port reviewed audio match links to library links.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-06
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from alembic import op

from music_manager_backend.domain.services.title_normalizer import normalize_match_title

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    migrated_at = datetime.now(UTC).isoformat()
    rows = connection.exec_driver_sql(
        """
        SELECT
            match_links.song_id,
            match_links.method,
            match_links.confidence,
            audio_files.path AS audio_path,
            audio_files.title AS audio_title,
            audio_files.duration_seconds AS audio_duration_seconds
        FROM match_links
        JOIN audio_files ON audio_files.id = match_links.audio_file_id
        WHERE match_links.reviewed = 1
        """
    ).mappings()

    for row in rows:
        library_track_id = _matching_library_track_id(
            connection,
            audio_path=row["audio_path"],
            audio_title=row["audio_title"],
            audio_duration_seconds=row["audio_duration_seconds"],
        )
        if library_track_id is None:
            continue
        connection.exec_driver_sql(
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
            VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(song_id, library_track_id) DO UPDATE SET
                method = excluded.method,
                confidence = excluded.confidence,
                reviewed = 1,
                updated_at = excluded.updated_at
            """,
            (
                row["song_id"],
                library_track_id,
                "manual",
                row["confidence"] or 1.0,
                migrated_at,
                migrated_at,
            ),
        )


def downgrade() -> None:
    # Data migration only. Do not delete reviewed library mappings on downgrade because
    # they may have been edited by the user after the port.
    pass


def _matching_library_track_id(
    connection,
    *,
    audio_path: str,
    audio_title: str | None,
    audio_duration_seconds: int | None,
) -> str | None:
    path_matches = connection.exec_driver_sql(
        """
        SELECT id FROM library_tracks
        WHERE canonical_path = ? AND status = 'active'
        """,
        (audio_path,),
    ).fetchall()
    if len(path_matches) == 1:
        return str(path_matches[0][0])

    if audio_duration_seconds is None:
        return None
    normalized_title = normalize_match_title(audio_title or "")
    if not normalized_title:
        return None
    identity_matches = connection.exec_driver_sql(
        """
        SELECT id FROM library_tracks
        WHERE normalized_title = ?
            AND duration_seconds = ?
            AND status = 'active'
        """,
        (normalized_title, audio_duration_seconds),
    ).fetchall()
    return str(identity_matches[0][0]) if len(identity_matches) == 1 else None
