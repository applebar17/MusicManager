"""Persist SoundCloud source discovery results.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "soundcloud_source_discoveries",
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("song_id", sa.Text(), nullable=False),
        sa.Column("track_url", sa.Text(), nullable=False),
        sa.Column("track_urn", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("artist", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("purchase_title", sa.Text(), nullable=True),
        sa.Column("purchase_url", sa.Text(), nullable=True),
        sa.Column("downloadable", sa.Integer(), nullable=True),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("links_json", sa.Text(), nullable=False),
        sa.Column("tags_json", sa.Text(), nullable=False),
        sa.Column("release_metadata_json", sa.Text(), nullable=False),
        sa.Column("warnings_json", sa.Text(), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"]),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
        sa.PrimaryKeyConstraint("environment_id", "song_id"),
    )


def downgrade() -> None:
    op.drop_table("soundcloud_source_discoveries")
