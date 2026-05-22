"""Add audio metadata fields.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audio_files", sa.Column("album", sa.Text(), nullable=True))
    op.add_column("audio_files", sa.Column("bpm", sa.Integer(), nullable=True))
    op.add_column("audio_files", sa.Column("key", sa.Text(), nullable=True))
    op.add_column("audio_files", sa.Column("comment", sa.Text(), nullable=True))
    op.add_column("audio_files", sa.Column("raw_metadata_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("audio_files", "raw_metadata_json")
    op.drop_column("audio_files", "comment")
    op.drop_column("audio_files", "key")
    op.drop_column("audio_files", "bpm")
    op.drop_column("audio_files", "album")
