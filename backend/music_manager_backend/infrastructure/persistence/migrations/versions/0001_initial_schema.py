"""Initial local persistence schema.

Revision ID: 0001
Revises:
Create Date: 2026-05-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "environments",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("deprecated_folder_name", sa.Text(), nullable=False),
        sa.Column("default_export_profile", sa.Text(), nullable=False),
    )
    op.create_table(
        "remote_playlists",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
    )
    op.create_table(
        "songs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("artist", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("source_track_id", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("local_title_override", sa.Text(), nullable=True),
        sa.Column("local_artist_override", sa.Text(), nullable=True),
    )
    op.create_table(
        "playlists",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("remote_playlist_id", sa.Text(), nullable=True),
        sa.Column("local_name_override", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"]),
        sa.ForeignKeyConstraint(["remote_playlist_id"], ["remote_playlists.id"]),
    )
    op.create_table(
        "playlist_items",
        sa.Column("playlist_id", sa.Text(), nullable=False),
        sa.Column("song_id", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("remote_membership_active", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
        sa.PrimaryKeyConstraint("playlist_id", "song_id"),
    )
    op.create_table(
        "audio_files",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("modified_at", sa.Float(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("artist", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"]),
    )
    op.create_table(
        "match_links",
        sa.Column("song_id", sa.Text(), nullable=False),
        sa.Column("audio_file_id", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reviewed", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
        sa.ForeignKeyConstraint(["audio_file_id"], ["audio_files.id"]),
        sa.PrimaryKeyConstraint("song_id", "audio_file_id"),
    )
    op.create_table(
        "sync_snapshots",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("remote_playlist_id", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["remote_playlist_id"], ["remote_playlists.id"]),
    )
    op.create_table(
        "export_plans",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"]),
    )
    op.create_table(
        "export_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("export_plan_id", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["export_plan_id"], ["export_plans.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("export_plan_items")
    op.drop_table("export_plans")
    op.drop_table("sync_snapshots")
    op.drop_table("match_links")
    op.drop_table("audio_files")
    op.drop_table("playlist_items")
    op.drop_table("playlists")
    op.drop_table("songs")
    op.drop_table("remote_playlists")
    op.drop_table("environments")
