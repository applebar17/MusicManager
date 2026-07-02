"""Add local playlist item membership.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "playlist_items",
        sa.Column("local_membership_active", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "playlist_items",
        sa.Column("added_by_local_audio_file_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "playlist_items",
        sa.Column("remote_removed_at", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("playlist_items", "remote_removed_at")
    op.drop_column("playlist_items", "added_by_local_audio_file_id")
    op.drop_column("playlist_items", "local_membership_active")
