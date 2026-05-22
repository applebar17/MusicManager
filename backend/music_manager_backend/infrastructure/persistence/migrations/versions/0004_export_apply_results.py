"""Add export apply result persistence.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "export_apply_runs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("export_plan_id", sa.Text(), nullable=False),
        sa.Column("environment_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["export_plan_id"], ["export_plans.id"]),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"]),
    )
    op.create_table(
        "export_apply_item_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("apply_run_id", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["apply_run_id"], ["export_apply_runs.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("export_apply_item_results")
    op.drop_table("export_apply_runs")
