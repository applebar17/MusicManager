"""Add editable export plan state.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("export_plans", sa.Column("locked_at", sa.Text(), nullable=True))
    op.add_column("export_plans", sa.Column("validation_error_code", sa.Text(), nullable=True))
    op.add_column("export_plans", sa.Column("validation_error_message", sa.Text(), nullable=True))
    op.add_column("export_plan_items", sa.Column("public_id", sa.Text(), nullable=True))
    op.add_column(
        "export_plan_items",
        sa.Column("included", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "export_plan_items",
        sa.Column("validation_error_code", sa.Text(), nullable=True),
    )
    op.add_column(
        "export_plan_items",
        sa.Column("validation_error_message", sa.Text(), nullable=True),
    )
    op.execute(
        """
        UPDATE export_plan_items
        SET public_id = 'export_plan_item_' || lower(hex(randomblob(16)))
        WHERE public_id IS NULL
        """
    )
    op.add_column(
        "export_apply_item_results",
        sa.Column("export_plan_item_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("export_apply_item_results", "export_plan_item_id")
    op.drop_column("export_plan_items", "validation_error_message")
    op.drop_column("export_plan_items", "validation_error_code")
    op.drop_column("export_plan_items", "included")
    op.drop_column("export_plan_items", "public_id")
    op.drop_column("export_plans", "validation_error_message")
    op.drop_column("export_plans", "validation_error_code")
    op.drop_column("export_plans", "locked_at")
