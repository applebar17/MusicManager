"""Add library alignment state.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "library_tracks",
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "library_tracks",
        sa.Column("modified_at", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "library_tracks",
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
    )
    op.add_column("library_tracks", sa.Column("first_seen_at", sa.Text(), nullable=True))
    op.add_column("library_tracks", sa.Column("last_seen_at", sa.Text(), nullable=True))
    op.add_column("library_tracks", sa.Column("missing_at", sa.Text(), nullable=True))
    op.create_index("ix_library_tracks_status", "library_tracks", ["library_id", "status"])

    op.create_table(
        "library_alignment_runs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("library_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("scanned_library_count", sa.Integer(), nullable=False),
        sa.Column("scanned_usb_count", sa.Integer(), nullable=False),
        sa.Column("copied_count", sa.Integer(), nullable=False),
        sa.Column("reused_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_collision_count", sa.Integer(), nullable=False),
        sa.Column("skipped_error_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"]),
    )
    op.create_table(
        "library_alignment_items",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=True),
        sa.Column("library_track_id", sa.Text(), nullable=True),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("reason_message", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("artist", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("normalized_title", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["library_alignment_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["library_track_id"], ["library_tracks.id"]),
    )
    op.create_index(
        "ix_library_alignment_runs_library_started",
        "library_alignment_runs",
        ["library_id", "started_at"],
    )
    op.create_index(
        "ix_library_alignment_items_run_id",
        "library_alignment_items",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_library_alignment_items_run_id", table_name="library_alignment_items")
    op.drop_index(
        "ix_library_alignment_runs_library_started",
        table_name="library_alignment_runs",
    )
    op.drop_table("library_alignment_items")
    op.drop_table("library_alignment_runs")
    op.drop_index("ix_library_tracks_status", table_name="library_tracks")
    op.drop_column("library_tracks", "missing_at")
    op.drop_column("library_tracks", "last_seen_at")
    op.drop_column("library_tracks", "first_seen_at")
    op.drop_column("library_tracks", "status")
    op.drop_column("library_tracks", "modified_at")
    op.drop_column("library_tracks", "size_bytes")
