"""Add shared library tables.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "libraries",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "library_tracks",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("library_id", sa.Text(), nullable=False),
        sa.Column("canonical_path", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("artist", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("normalized_title", sa.Text(), nullable=True),
        sa.Column("file_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("library_id", "canonical_path"),
    )
    op.create_index(
        "ix_library_tracks_library_id",
        "library_tracks",
        ["library_id"],
    )
    op.create_index(
        "ix_library_tracks_canonical_path",
        "library_tracks",
        ["canonical_path"],
    )
    op.create_index(
        "ix_library_tracks_identity",
        "library_tracks",
        ["normalized_title", "duration_seconds"],
    )


def downgrade() -> None:
    op.drop_index("ix_library_tracks_identity", table_name="library_tracks")
    op.drop_index("ix_library_tracks_canonical_path", table_name="library_tracks")
    op.drop_index("ix_library_tracks_library_id", table_name="library_tracks")
    op.drop_table("library_tracks")
    op.drop_table("libraries")
