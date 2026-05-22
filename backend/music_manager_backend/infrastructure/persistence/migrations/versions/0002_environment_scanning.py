"""Add environment archive and scan state.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("environments", sa.Column("archived_at", sa.Text(), nullable=True))
    op.create_table(
        "scan_runs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("added_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("changed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("removed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("moved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unchanged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_active_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"]),
    )
    op.add_column(
        "audio_files",
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
    )
    op.add_column("audio_files", sa.Column("first_seen_scan_id", sa.Text(), nullable=True))
    op.add_column("audio_files", sa.Column("last_seen_scan_id", sa.Text(), nullable=True))
    op.add_column("audio_files", sa.Column("removed_at", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("audio_files", "removed_at")
    op.drop_column("audio_files", "last_seen_scan_id")
    op.drop_column("audio_files", "first_seen_scan_id")
    op.drop_column("audio_files", "status")
    op.drop_table("scan_runs")
    op.drop_column("environments", "archived_at")
