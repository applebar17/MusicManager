"""Add library metadata import tables.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "library_metadata_import_runs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("library_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("alignment_run_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("asset_count", sa.Integer(), nullable=False),
        sa.Column("index_entry_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"]),
        sa.ForeignKeyConstraint(["alignment_run_id"], ["library_alignment_runs.id"]),
    )
    op.create_table(
        "library_metadata_assets",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("library_id", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("modified_at", sa.Float(), nullable=False),
        sa.Column("imported_at", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["library_metadata_import_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "library_metadata_index_entries",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("library_id", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("source_asset_id", sa.Text(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("library_track_id", sa.Text(), nullable=True),
        sa.Column("entry_key", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("imported_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["library_id"], ["libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["library_metadata_assets.id"]),
        sa.ForeignKeyConstraint(["library_track_id"], ["library_tracks.id"]),
        sa.UniqueConstraint("library_id", "provider", "entry_key"),
    )
    op.create_index(
        "ix_library_metadata_import_runs_library_started",
        "library_metadata_import_runs",
        ["library_id", "started_at"],
    )
    op.create_index(
        "ix_library_metadata_assets_library_provider",
        "library_metadata_assets",
        ["library_id", "provider"],
    )
    op.create_index(
        "ix_library_metadata_index_entries_library_provider",
        "library_metadata_index_entries",
        ["library_id", "provider"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_library_metadata_index_entries_library_provider",
        table_name="library_metadata_index_entries",
    )
    op.drop_index(
        "ix_library_metadata_assets_library_provider",
        table_name="library_metadata_assets",
    )
    op.drop_index(
        "ix_library_metadata_import_runs_library_started",
        table_name="library_metadata_import_runs",
    )
    op.drop_table("library_metadata_index_entries")
    op.drop_table("library_metadata_assets")
    op.drop_table("library_metadata_import_runs")
