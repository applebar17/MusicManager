"""Add song to library track links.

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "song_library_links",
        sa.Column("song_id", sa.Text(), nullable=False),
        sa.Column("library_track_id", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reviewed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["library_track_id"], ["library_tracks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("song_id", "library_track_id"),
    )
    op.create_index("ix_song_library_links_song", "song_library_links", ["song_id"])
    op.create_index(
        "ix_song_library_links_library_track",
        "song_library_links",
        ["library_track_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_song_library_links_library_track", table_name="song_library_links")
    op.drop_index("ix_song_library_links_song", table_name="song_library_links")
    op.drop_table("song_library_links")
